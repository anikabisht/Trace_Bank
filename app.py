#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TRACE BANK - MAIN FASTAPI BACKEND
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
from datetime import datetime
import hashlib

from decision_engine import make_decision, update_policy
from ml_engine import ContinuousMLEngine, calculate_behavior_score



# Import our engines
try:
    from data_tracker import RealDataTracker
except Exception:
    RealDataTracker=None
try:
    from counterfactual import CounterfactualEngine
except Exception:
    CounterfactualEngine=None
try:
    from scenario_engine import ScenarioEngine
except Exception:
    ScenarioEngine=None
import os

# Initialize engines
from ml_engine import ContinuousMLEngine
ml_engine = ContinuousMLEngine()
data_tracker = RealDataTracker()
counterfactual_engine = CounterfactualEngine()
scenario_engine = ScenarioEngine()

# =============== CONSTANTS ===============
USD_TO_INR = 83.5  # Currency conversion rate

# =============== DATA MODELS ===============
class TransactionRequest(BaseModel):
    user_id: str
    amount: float
    merchant_category: str = "retail"
    location_permission: bool = False
    scenario_type: str = "normal"
    
    # ✅ REAL GPS FIELDS
    latitude: float | None = None
    longitude: float | None = None


class ViewToggle(BaseModel):
    view: str  # "customer" or "bank"

# =============== CREATE APP ===============
app = FastAPI(
    title="Trace Bank",
    description="Real-time fraud detection with ML-powered counterfactuals",
    version="3.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============== DATA STORAGE ===============
class Database:
    def __init__(self):
        self.transactions = []
        self.users = {}
    
    def save_transaction(self, transaction: Dict) -> str:
        transaction_id = hashlib.md5(
            f"{transaction['user_id']}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        transaction['id'] = transaction_id
        transaction['timestamp'] = datetime.now().isoformat()
        self.transactions.append(transaction)
        
        # Update user history
        user_id = transaction['user_id']
        if user_id not in self.users:
            self.users[user_id] = []
        self.users[user_id].append(transaction)
        
        # Keep only last 50 transactions per user
        if len(self.users[user_id]) > 50:
            self.users[user_id] = self.users[user_id][-50:]
        
        return transaction_id
    
    def get_user_history(self, user_id: str) -> List[Dict]:
        return self.users.get(user_id, [])

db = Database()

# =============== RISK CALCULATION ===============
def calculate_risk_score(tracking_data: Dict, amount: float, 
                        user_id: str, merchant: str) -> tuple:
    """Simple, precise risk score calculation"""
    
    # RULE 1: Amount >= 2.5 Lakh = ALWAYS HIGH RISK (60+ points)
    HIGH_AMOUNT_THRESHOLD = 250000  # 2.5 Lakh rupees
    
    if amount >= HIGH_AMOUNT_THRESHOLD:
        # Fixed high risk for large amounts
        total_risk = 65.0
        component_risks = {
            'amount': 40,
            'location': 5,
            'time': 5,
            'merchant': 5,
            'behavior': 5,
            'velocity': 5
        }
        return total_risk, component_risks
    
    # RULE 2: For amounts below 2.5L, calculate based on user history
    user_history = db.get_user_history(user_id)
    
    # Amount risk (0-30)
    if not user_history:
        # New user: any amount is slightly risky
        amount_risk = min(20, (amount / 10000) * 2)  # Scale with amount
    else:
        amounts = [t.get('amount', 0) for t in user_history if t.get('amount', 0) > 0]
        if amounts:
            avg_amount = sum(amounts) / len(amounts)
            ratio = amount / avg_amount
            
            if ratio <= 1.0:
                amount_risk = 0
            elif ratio <= 1.5:
                amount_risk = (ratio - 1.0) * 10
            elif ratio <= 2.0:
                amount_risk = 5 + (ratio - 1.5) * 10
            else:
                amount_risk = 30  # Way above average
        else:
            amount_risk = 10
    
    # Location risk (0-15) - VPN check
    vpn_prob = ml_engine.detect_vpn(
        tracking_data['ip']['ip_address'],
        tracking_data['location']
    )
    location_risk = min(15, vpn_prob * 20)  # VPN = up to 15 points
    
    # Merchant risk (0-10)
    merchant_risk_map = {
        'gambling': 10, 'cryptocurrency': 8,
        'electronics': 5, 'retail': 2,
        'groceries': 1, 'restaurants': 2
    }
    merchant_risk = merchant_risk_map.get(merchant.lower(), 3)
    
    # Time risk (0-10)
    time_data = tracking_data['time']
    time_risk = 2 if time_data['is_night'] else 0
    
    # Behavior risk (0-10)
    behavior_score, behavior_reasons = ml_engine.analyze_behavior(tracking_data['behavior'])
    behavior_risk = max(0, min(10, (behavior_score - 40) / 5))
    
    # Velocity risk (0-10)
    velocity_risk = 0
    user_txns = [t for t in db.transactions[-100:] if t.get('user_id') == user_id]
    if len(user_txns) > 5:
        velocity_risk = min(10, (len(user_txns) - 5) / 5)
    
    # Component risks
    component_risks = {
        'amount': round(amount_risk, 1),
        'location': round(location_risk, 1),
        'merchant': round(merchant_risk, 1),
        'time': round(time_risk, 1),
        'behavior': round(behavior_risk, 1),
        'velocity': round(velocity_risk, 1)
    }
    
    # Simple sum = total risk
    total_risk = sum(component_risks.values())
    total_risk = min(100, max(0, total_risk))
    
    return total_risk, component_risks

# =============== DECISION MAKING ===============
def make_decision(risk_score: float) -> tuple:
    # Stricter thresholds to catch high-amount fraud
    if risk_score < 20:
        return "APPROVED", "LOW_RISK"
    elif risk_score < 40:
        return "APPROVED", "MEDIUM_LOW"
    elif risk_score < 60:
        return "PENDING_REVIEW", "MEDIUM_HIGH"
    elif risk_score < 80:
        return "DECLINED", "HIGH_RISK"
    else:
        return "DECLINED", "VERY_HIGH_RISK"

# =============== API ENDPOINTS ===============
@app.get("/")
async def root():
    return {
        "service": "Trace Bank",
        "version": "3.0",
        "status": "running",
        "features": [
            "Real ML models (4 models)",
            "Auto-tracking (GPS/IP/Behavior)",
            "Counterfactual explanations (MVP)",
            "Churn impact visualization",
            "Bank Customer toggle views"
        ]
    }

@app.get("/api/location")
async def get_location(http_request: Request):
    """
    Get user's location based on their IP address
    """
    try:
        # Get actual client IP
        client_ip = http_request.headers.get("x-forwarded-for", "").split(",")[0].strip() or \
                   http_request.headers.get("x-real-ip", "") or \
                   http_request.client.host
        
        # If localhost, return default Mumbai location for testing
        if client_ip in ['127.0.0.1', 'localhost', '::1', '0.0.0.0']:
            return {
                "ip": client_ip,
                "location": "Mumbai",
                "country": "India",
                "latitude": 19.0760,
                "longitude": 72.8777,
                "accuracy": 100,
                "timestamp": datetime.now().isoformat(),
                "source": "localhost_default"
            }
        
        # Get location from IP for real IPs
        location = data_tracker.get_location_data("guest", client_ip)
        
        return {
            "ip": client_ip,
            "location": location['city'],
            "country": location['country'],
            "latitude": location['latitude'],
            "longitude": location['longitude'],
            "accuracy": location['accuracy'],
            "timestamp": datetime.now().isoformat(),
            "source": "ip_geolocation"
        }
    except Exception as e:
        # Return default location on error
        return {
            "ip": "unknown",
            "location": "Mumbai",
            "country": "India",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "accuracy": 100,
            "timestamp": datetime.now().isoformat(),
            "source": "fallback_default"
        }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/transaction")
async def process_transaction(request: TransactionRequest, http_request: Request):
    """
    Process transaction with auto-tracking and ML analysis
    Supports synthetic scenarios for fraud_ring and behavioral_anomaly
    """
    try:
        # Check location permission first
        if not request.location_permission:
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Location permission required",
                    "message": "Please grant location permission to process transactions",
                    "location_required": True
                }
            )
        
        # Get actual client IP from request headers
        client_ip = http_request.headers.get("x-forwarded-for", "").split(",")[0].strip() or \
                   http_request.headers.get("x-real-ip", "") or \
                   http_request.client.host
        
        # Handle localhost IPs
        if client_ip in ['127.0.0.1', 'localhost', '::1', '0.0.0.0']:
            client_ip = '192.168.1.100'  # Use a mock IP for localhost
        
        # Check if this is a synthetic scenario
        scenario_type = request.scenario_type
        scenario_metadata = None
        
        # 1. AUTO-TRACK user data (with permission) - Use real IP geolocation
        # ✅ REAL LOCATION HANDLING (GPS + IP fallback)

    # If frontend sends real GPS location
    # ================= REAL LOCATION LOGIC =================

            # ================= REAL LOCATION LOGIC =================

        # If frontend sends real GPS location
        if request.latitude is not None and request.longitude is not None:
            location_data = {
                "city": "Real GPS Location",
                "country": "India",
                "latitude": request.latitude,
                "longitude": request.longitude,
                "gps_enabled": True
            }
        else:
            # fallback to IP-based location
            try:
                location_data = data_tracker.get_location_data(request.user_id, client_ip)
            except Exception as e:
                print("Location error:", e)
                location_data = {
                    "city": "Unknown",
                    "country": "Unknown",
                    "latitude": 0,
                    "longitude": 0,
                    "gps_enabled": False
                }

        # ======================================================

# ======================================================


        
        ip_data = {
            'ip_address': client_ip,
            'is_vpn': False
        }
        
        # Default tracking data
        behavior_data = data_tracker.get_behavior_data(request.user_id)
        device_data = data_tracker.get_device_data(request.user_id)
        
        # SCENARIO ENGINE: Generate synthetic data for fraud_ring or behavioral_anomaly
        if scenario_type == 'fraud_ring':
            # Generate synthetic fraud ring data
            synthetic_data = scenario_engine.generate_fraud_ring_scenario(
                request.user_id,
                {
                    'user_id': request.user_id,
                    'amount': request.amount,
                    'merchant_category': request.merchant_category
                }
            )
            scenario_metadata = synthetic_data.get('scenario_metadata')
            # Override IP and device with synthetic shared resources
            ip_data['ip_address'] = synthetic_data.get('ip_address', client_ip)
            device_data['device_id'] = synthetic_data.get('device_id', device_data['device_id'])
            
        elif scenario_type == 'behavioral_anomaly':
            # Generate synthetic behavioral anomaly data
            synthetic_data = scenario_engine.generate_behavioral_anomaly_scenario(
                request.user_id,
                {
                    'user_id': request.user_id,
                    'amount': request.amount,
                    'merchant_category': request.merchant_category
                }
            )
            scenario_metadata = synthetic_data.get('scenario_metadata')
            # Override behavior with synthetic anomaly patterns
            if 'synthetic_behavior' in synthetic_data:
                behavior_data = synthetic_data['synthetic_behavior']
            if 'synthetic_device' in synthetic_data:
                device_data = synthetic_data['synthetic_device']
        
        tracking_data = {
            'location': location_data,
            'ip': ip_data,
            'behavior': behavior_data,
            'device': device_data,
            'time': data_tracker.get_time_context()
        }
        
        # 2. Calculate risk score
        risk_score, component_risks = calculate_risk_score(
            tracking_data,
            request.amount,
            request.user_id,
            request.merchant_category
        )
        
        # FRAUD SCENARIOS: Always result in HIGH RISK and DECLINED
        if scenario_type == 'fraud_ring':
            # Fraud ring = automatic high risk
            risk_score = max(85, risk_score)  # Minimum 85 for fraud ring
            component_risks['fraud_ring'] = 40  # Add fraud ring component
            component_risks['shared_device'] = 15
            component_risks['shared_ip'] = 15
        elif scenario_type == 'behavioral_anomaly':
            # Behavioral anomaly = automatic high risk
            risk_score = max(75, risk_score)  # Minimum 75 for anomaly
            component_risks['behavior'] = max(25, component_risks.get('behavior', 0))
            component_risks['anomaly_detected'] = 20
        
        # 3. Make decision
        # 3. Make decision (SAFE DEFAULTS)
        decision = "APPROVED"
        risk_level = "LOW_RISK"

        try:
            decision, risk_level = make_decision(float(risk_score))
        except Exception as e:
            print("Decision error:", e)

                
        # Force DECLINED for fraud scenarios
        if scenario_type in ['fraud_ring', 'behavioral_anomaly']:
            decision = 'DECLINED'
            risk_level = 'FRAUD_DETECTED' if scenario_type == 'fraud_ring' else 'ANOMALY_DETECTED'
            # ✅ FINAL SAFETY CHECK
            if 'risk_level' not in locals():
                risk_level = "UNKNOWN"

            if 'decision' not in locals():
                decision = "REVIEW"

        # 4. Detect fraud rings (ML Model 3)
        fraud_ring_data = ml_engine.detect_fraud_ring({
            'user_id': request.user_id,
            'ip_address': tracking_data['ip']['ip_address'],
            'device_id': tracking_data['device']['device_id']
        })
        
        # 5. Generate counterfactuals (MVP ENGINE) - Returns tuple (customer, bank)
        user_history = db.get_user_history(request.user_id)
        customer_counterfactuals, bank_counterfactuals = counterfactual_engine.generate_counterfactuals(
            {
                'user_id': request.user_id,
                'amount': request.amount,
                'merchant_category': request.merchant_category,
                'hour': tracking_data['time']['hour'],
                'risk_score': risk_score
            },
            risk_score,
            component_risks,
            user_history
        )
        
        # 6. Calculate churn impact
        churn_impact = counterfactual_engine.calculate_churn_impact(
            decision, risk_score, user_value=1000.0
        )
        
        # 7. Prepare transaction data
        transaction_data = {
            'user_id': request.user_id,
            'amount': float(request.amount),
            'merchant_category': request.merchant_category,
            'risk_score': float(risk_score),
            'risk_level': risk_level,
            'decision': decision,
            'vpn_probability': float(ml_engine.detect_vpn(
                tracking_data['ip']['ip_address'],
                tracking_data['location']
            )),
            'behavior_score': float(ml_engine.analyze_behavior(tracking_data['behavior'])[0]),
            'gps_enabled': bool(tracking_data['location'].get('gps_enabled', True)),
            'city': str(tracking_data['location'].get('city', 'Unknown')),
            'country': str(tracking_data['location'].get('country', 'Unknown')),

            'timestamp': datetime.now().isoformat()
        }
        
        # ================= ML CONTINUOUS TRAINING + CSV SAVING =================

        # try:
        #     features = {
        #         "amount": float(request.amount),
        #         "velocity": float(component_risks.get("velocity", 0)),
        #         "location_risk": float(component_risks.get("location", 0)),
        #         "behavior_score": float(component_risks.get("behavior", 0))
        #     }

        #     # Label: 1 = fraud, 0 = normal
        #     label = 1 if decision in ["DECLINED", "BLOCK"] else 0

        #     ml_engine.save_transaction(features, label)

        # except Exception as e:
        #     print("ML training error:", e)

        # =====================================================================
        
        # 8. Save to database
        transaction_id = db.save_transaction(transaction_data)
        
        # 9. Prepare response with INR currency
        response = {
            'transaction_id': str(transaction_id),
            'user_id': str(request.user_id),
            'amount_inr': float(request.amount),
            'currency': 'INR',
            'risk_score': float(round(risk_score, 2)),
            'risk_level': str(risk_level),
            'decision': str(decision),
            'scenario_type': scenario_type,
            'component_risks': {
                'amount': float(component_risks.get('amount', 0)),
                'location': float(component_risks.get('location', 0)),
                'merchant': float(component_risks.get('merchant', 0)),
                'time': float(component_risks.get('time', 0)),
                'behavior': float(component_risks.get('behavior', 0)),
                'velocity': float(component_risks.get('velocity', 0))
            },
            'customer_counterfactuals': customer_counterfactuals if isinstance(customer_counterfactuals, list) else [],
            'bank_counterfactuals': bank_counterfactuals if isinstance(bank_counterfactuals, list) else [],
            'churn_impact': churn_impact if isinstance(churn_impact, dict) else {},
            'fraud_ring_alert': fraud_ring_data if isinstance(fraud_ring_data, dict) and fraud_ring_data.get('suspicion_score', 0) > 50 else None,
            'tracking_summary': {
                'location': f"{tracking_data['location'].get('city', 'Unknown')}, {tracking_data['location'].get('country', 'Unknown')}",
                'gps_enabled': bool(tracking_data['location'].get('gps_enabled', True)),
                'behavior_match': 'NORMAL' if float(component_risks.get('behavior', 0)) < 8 else 'ANOMALOUS',
                'device_trust': 'KNOWN' if not tracking_data['device'].get('is_new_device', False) else 'NEW',
                'time_context': 'NORMAL' if float(component_risks.get('time', 0)) < 5 else 'UNUSUAL'
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Add scenario-specific analysis for BANK mode (will be filtered by frontend for CUSTOMER mode)
        if scenario_metadata:
            if scenario_type == 'fraud_ring':
                response['fraud_ring_analysis'] = scenario_engine.get_fraud_ring_analysis(scenario_metadata)
                # Boost fraud ring detection score for synthetic scenario
                response['fraud_ring_alert'] = {
                    'suspicion_score': scenario_metadata.get('confidence', 85),
                    'ring_size': scenario_metadata.get('ring_size', 5),
                    'role_density': scenario_metadata.get('role_density', {}),
                    'shared_connections': scenario_metadata.get('ring_members', [])[:5],
                    'connection_count': scenario_metadata.get('shared_device_users', 0)
                }
            elif scenario_type == 'behavioral_anomaly':
                response['behavioral_anomaly_analysis'] = scenario_engine.get_behavioral_anomaly_analysis(scenario_metadata)
                # Update tracking summary to reflect anomaly
                response['tracking_summary']['behavior_match'] = 'ANOMALOUS'
                response['tracking_summary']['anomaly_type'] = scenario_metadata.get('anomaly_type', 'unknown')
                response['tracking_summary']['anomaly_score'] = scenario_metadata.get('anomaly_score', 0)
        
        return JSONResponse(content=response)
        
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        try:
            print(f"ERROR: {error_msg}")
        except UnicodeEncodeError:
            print("ERROR: Exception occurred (see response)")
        return JSONResponse(
            status_code=500,
            content={
                'error': 'Internal server error',
                'message': str(e),
                'details': str(type(e).__name__)
            }
        )

@app.get("/api/user/{user_id}/history")
async def get_user_history(user_id: str):
    """Get user transaction history with audit log"""
    history = db.get_user_history(user_id)
    
    if not history:
        return {"user_id": user_id, "message": "No transaction history", "transactions": []}
    
    # Calculate statistics
    amounts = [t.get('amount', 0) for t in history if t.get('amount', 0) > 0]
    avg_amount = sum(amounts) / len(amounts) if amounts else 0
    
    # Format transactions for audit log display
    formatted_history = []
    for txn in history:
        formatted_history.append({
            'transaction_id': txn.get('id'),
            'timestamp': txn.get('timestamp'),
            'amount': txn.get('amount'),
            'merchant': txn.get('merchant_category'),
            'decision': txn.get('decision'),
            'risk_score': txn.get('risk_score'),
            'risk_level': txn.get('risk_level'),
            'location': f"{txn.get('city', 'Unknown')}, {txn.get('country', 'Unknown')}",
            'status': 'APPROVED' if txn.get('decision') == 'APPROVED' else 'DECLINED' if txn.get('decision') == 'DECLINED' else 'PENDING'
        })
    
    return {
        'user_id': user_id,
        'total_transactions': len(history),
        'average_amount': round(avg_amount, 2),
        'statistics': {
            'approved': len([t for t in history if t.get('decision') == 'APPROVED']),
            'declined': len([t for t in history if t.get('decision') == 'DECLINED']),
            'pending': len([t for t in history if t.get('decision') == 'PENDING_REVIEW'])
        },
        'transactions': formatted_history  # Full audit log
    }

@app.get("/api/audit-log")
async def get_audit_log(limit: int = 20):
    """Get global audit log of all transactions"""
    all_txns = db.transactions[-limit:]  # Get last N transactions
    
    formatted_log = []
    for txn in all_txns:
        formatted_log.append({
            'transaction_id': txn.get('id'),
            'user_id': txn.get('user_id'),
            'timestamp': txn.get('timestamp'),
            'amount': txn.get('amount'),
            'decision': txn.get('decision'),
            'risk_score': round(txn.get('risk_score', 0), 1),
            'location': txn.get('city', 'Unknown'),
            'status': 'APPROVED' if txn.get('decision') == 'APPROVED' else 'DECLINED' if txn.get('decision') == 'DECLINED' else 'PENDING'
        })
    
    return {
        'total_transactions': len(db.transactions),
        'audit_log': formatted_log
    }

@app.get("/api/fraud-rings")
async def get_fraud_rings():
    """Get detected fraud rings"""
    # This would query the ML engine's fraud graph
    # For demo, return simulated data
    return {
        'fraud_rings_detected': 2,
        'high_risk_rings': [
            {
                'type': 'IP_SHARING',
                'users': ['user_001', 'user_002', 'user_003'],
                'shared_ip': '192.168.1.100',
                'suspicion_score': 85,
                'description': '3 users sharing same VPN IP'
            }
        ],
        'total_monitored_users': len(db.users),
        'suspicious_patterns': ['IP sharing', 'device sharing', 'velocity clusters']
    }

@app.get("/dashboard")
async def dashboard():
    """Serve the interactive dashboard"""
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    with open(dashboard_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# =============== RUN SERVER ===============
if __name__ == "__main__":
    try:
        print("\n" + "="*60)
        print("TRACE BANK - FRAUD DETECTION SYSTEM")
        print("="*60)
        print("Backend: http://127.0.0.1:8000")
        print("Dashboard: http://localhost:8000/dashboard")
        print("API Docs: http://localhost:8000/docs")
        print("\nFEATURES READY:")
        print("  1. 4 REAL ML Models (trained)")
        print("  2. Auto-tracking (GPS/IP/Behavior)")
        print("  3. Counterfactual Engine (MVP)")
        print("  4. Churn Impact Visualization")
        print("  5. Bank vs Customer View Toggle")
        print("  6. Fraud Ring Detection")
        print("\nDEMO SCENARIOS:")
        print("  - Normal: 100 INR retail - APPROVED")
        print("  - VPN: 1000 INR gambling - DECLINED with counterfactuals")
        print("  - Fraud: Multiple users sharing IP - ALERT")
        print("="*60)
    except UnicodeEncodeError:
        pass
    
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)

@app.get("/api/policy")
async def get_policy():
    return update_policy()

@app.post("/api/policy/update")
async def update_policy_api(payload: dict):
    block_threshold = payload.get("block_threshold")
    review_threshold = payload.get("review_threshold")
    return update_policy(block_threshold, review_threshold)
