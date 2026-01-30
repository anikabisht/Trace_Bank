"""
TRACE BANK - SCENARIO ENGINE
Generates deterministic synthetic data for fraud ring and behavioral anomaly scenarios
Feeds synthetic data through actual ML pipeline for demonstration/testing
"""

import random
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import numpy as np

class ScenarioEngine:
    """
    Generates synthetic behavior patterns for fraud detection scenarios.
    Only used for fraud_ring and behavioral_anomaly scenarios, NOT normal transactions.
    """
    
    def __init__(self):
        # Fraud ring state - persists across calls to build up ring patterns
        self.fraud_ring_members = {}  # ring_id -> list of user data
        self.shared_devices = {}  # device_id -> list of user_ids
        self.shared_ips = {}  # ip -> list of user_ids
        
        # Behavioral anomaly patterns
        self.anomaly_patterns = {
            'robotic': {
                'typing_speed': 150,  # Very fast, consistent
                'mouse_consistency': 99,  # Too perfect
                'session_duration': 45,  # Very short
                'is_robotic': True
            },
            'unusual_timing': {
                'typing_speed': 30,  # Very slow (hesitant)
                'mouse_consistency': 40,  # Erratic
                'session_duration': 1800,  # Very long session
                'is_robotic': False
            },
            'device_mismatch': {
                'typing_speed': 60,
                'mouse_consistency': 70,
                'session_duration': 120,
                'is_robotic': False,
                'new_device': True
            }
        }
        
        # Role definitions for fraud rings
        self.ring_roles = ['mule', 'coordinator', 'beneficiary', 'money_launderer', 'recruiter']
    
    def generate_fraud_ring_scenario(self, base_user_id: str, transaction_data: Dict) -> Dict:
        """
        Generate synthetic fraud ring data.
        Creates multiple fake users sharing same device/IP to trigger fraud ring detection.
        
        Returns enhanced transaction data with fraud ring synthetic patterns.
        """
        # Create a deterministic ring ID based on the scenario
        ring_id = f"ring_{hashlib.md5(base_user_id.encode()).hexdigest()[:8]}"
        
        # Generate ring members (5-8 synthetic users)
        ring_size = random.randint(5, 8)
        
        # Shared device and IP for the ring
        shared_device_id = f"device_fraud_{hashlib.md5(ring_id.encode()).hexdigest()[:12]}"
        shared_ip = f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"
        
        # Generate synthetic ring members with roles
        ring_members = []
        role_distribution = {}
        
        for i in range(ring_size):
            member_id = f"ring_member_{ring_id}_{i}"
            role = self.ring_roles[i % len(self.ring_roles)]
            
            # Count role distribution
            role_distribution[role] = role_distribution.get(role, 0) + 1
            
            ring_members.append({
                'user_id': member_id,
                'role': role,
                'device_id': shared_device_id,
                'ip_address': shared_ip,
                'join_date': (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat()
            })
        
        # Store in shared tracking
        if shared_device_id not in self.shared_devices:
            self.shared_devices[shared_device_id] = []
        self.shared_devices[shared_device_id].extend([m['user_id'] for m in ring_members])
        
        if shared_ip not in self.shared_ips:
            self.shared_ips[shared_ip] = []
        self.shared_ips[shared_ip].extend([m['user_id'] for m in ring_members])
        
        # Calculate confidence based on patterns
        confidence = self._calculate_ring_confidence(ring_size, len(role_distribution))
        
        # Enhanced transaction data with fraud ring info
        enhanced_data = {
            **transaction_data,
            'device_id': shared_device_id,
            'ip_address': shared_ip,
            'scenario_metadata': {
                'type': 'fraud_ring',
                'ring_id': ring_id,
                'ring_size': ring_size,
                'role_density': role_distribution,
                'confidence': confidence,
                'ring_members': ring_members,
                'shared_device_users': len(self.shared_devices.get(shared_device_id, [])),
                'shared_ip_users': len(self.shared_ips.get(shared_ip, []))
            }
        }
        
        return enhanced_data
    
    def generate_behavioral_anomaly_scenario(self, user_id: str, transaction_data: Dict) -> Dict:
        """
        Generate synthetic behavioral anomaly data.
        Creates patterns that trigger the Isolation Forest anomaly detector.
        
        Returns enhanced transaction data with anomaly patterns.
        """
        # Randomly select anomaly type
        anomaly_type = random.choice(['robotic', 'unusual_timing', 'device_mismatch'])
        anomaly_pattern = self.anomaly_patterns[anomaly_type]
        
        # Generate synthetic behavior data
        synthetic_behavior = {
            'typing_speed': anomaly_pattern['typing_speed'] + random.uniform(-5, 5),
            'mouse_consistency': anomaly_pattern['mouse_consistency'] + random.uniform(-3, 3),
            'session_duration': anomaly_pattern['session_duration'] + random.uniform(-10, 10),
            'click_count': random.randint(2, 100) if anomaly_type == 'robotic' else random.randint(10, 30),
            'scroll_depth': 0.1 if anomaly_type == 'robotic' else random.uniform(0.3, 0.9),
            'is_robotic': anomaly_pattern['is_robotic'],
            'timestamp': datetime.now().isoformat()
        }
        
        # Calculate anomaly score (how anomalous this behavior is)
        anomaly_score = self._calculate_anomaly_score(synthetic_behavior, anomaly_type)
        
        # Device data for device_mismatch scenario
        device_data = {
            'device_id': f"device_anomaly_{hashlib.md5(user_id.encode()).hexdigest()[:12]}",
            'is_new_device': anomaly_pattern.get('new_device', False),
            'user_agent': 'Mozilla/5.0 (Anomaly Test)',
            'screen_resolution': '1920x1080',
            'fingerprint': hashlib.md5(f"{user_id}_anomaly".encode()).hexdigest()[:16]
        }
        
        # Enhanced transaction data with anomaly info
        enhanced_data = {
            **transaction_data,
            'synthetic_behavior': synthetic_behavior,
            'synthetic_device': device_data,
            'scenario_metadata': {
                'type': 'behavioral_anomaly',
                'anomaly_type': anomaly_type,
                'anomaly_score': anomaly_score,
                'anomaly_indicators': self._get_anomaly_indicators(anomaly_type, synthetic_behavior),
                'detection_confidence': min(95, anomaly_score + random.uniform(0, 10))
            }
        }
        
        return enhanced_data
    
    def _calculate_ring_confidence(self, ring_size: int, unique_roles: int) -> float:
        """Calculate confidence score for fraud ring detection"""
        # Base confidence from ring size (more members = higher confidence)
        size_factor = min(1.0, ring_size / 10) * 40
        
        # Role diversity factor (varied roles = more sophisticated ring)
        role_factor = min(1.0, unique_roles / 5) * 30
        
        # Shared resource factor (devices/IPs shared)
        sharing_factor = 25
        
        # Random variance
        variance = random.uniform(-5, 5)
        
        confidence = size_factor + role_factor + sharing_factor + variance
        return round(min(99, max(50, confidence)), 1)
    
    def _calculate_anomaly_score(self, behavior: Dict, anomaly_type: str) -> float:
        """Calculate anomaly score based on behavior patterns"""
        score = 0
        
        # Typing speed anomaly
        if behavior['typing_speed'] > 100 or behavior['typing_speed'] < 20:
            score += 25
        
        # Mouse consistency anomaly (too perfect or too erratic)
        if behavior['mouse_consistency'] > 95 or behavior['mouse_consistency'] < 50:
            score += 20
        
        # Session duration anomaly
        if behavior['session_duration'] < 60 or behavior['session_duration'] > 1200:
            score += 15
        
        # Robotic indicator
        if behavior['is_robotic']:
            score += 30
        
        # Type-specific bonuses
        if anomaly_type == 'robotic':
            score += 10
        elif anomaly_type == 'unusual_timing':
            score += 5
        
        return round(min(95, score + random.uniform(0, 10)), 1)
    
    def _get_anomaly_indicators(self, anomaly_type: str, behavior: Dict) -> List[str]:
        """Get human-readable anomaly indicators"""
        indicators = []
        
        if anomaly_type == 'robotic':
            indicators.append("Typing speed indicates automated input")
            indicators.append("Mouse movement pattern is too consistent")
            indicators.append("Session duration abnormally short")
            indicators.append("Behavior matches known bot patterns")
        elif anomaly_type == 'unusual_timing':
            indicators.append("Transaction timing outside normal user hours")
            indicators.append("Session duration abnormally long")
            indicators.append("Erratic interaction patterns detected")
        elif anomaly_type == 'device_mismatch':
            indicators.append("Device fingerprint does not match history")
            indicators.append("New device detected for this account")
            indicators.append("Browser/OS combination unusual for user")
        
        return indicators
    
    def get_fraud_ring_analysis(self, scenario_metadata: Dict) -> Dict:
        """
        Get detailed fraud ring analysis for BANK mode display.
        This is the data that should ONLY be shown in BANK mode.
        """
        if scenario_metadata.get('type') != 'fraud_ring':
            return {}
        
        return {
            'ring_id': scenario_metadata.get('ring_id'),
            'ring_size': scenario_metadata.get('ring_size'),
            'role_density': scenario_metadata.get('role_density'),
            'confidence': scenario_metadata.get('confidence'),
            'shared_device_count': scenario_metadata.get('shared_device_users', 0),
            'shared_ip_count': scenario_metadata.get('shared_ip_users', 0),
            'risk_factors': [
                f"Ring contains {scenario_metadata.get('ring_size', 0)} connected accounts",
                f"Multiple roles detected: {', '.join(scenario_metadata.get('role_density', {}).keys())}",
                f"Shared device across {scenario_metadata.get('shared_device_users', 0)} users",
                f"Shared IP address across {scenario_metadata.get('shared_ip_users', 0)} users"
            ],
            'recommended_actions': [
                "Flag all ring members for manual review",
                "Freeze suspicious accounts pending investigation",
                "Alert fraud investigation team",
                "Document evidence chain for potential legal action"
            ]
        }
    
    def get_behavioral_anomaly_analysis(self, scenario_metadata: Dict) -> Dict:
        """
        Get detailed behavioral anomaly analysis for BANK mode display.
        This is the data that should ONLY be shown in BANK mode.
        """
        if scenario_metadata.get('type') != 'behavioral_anomaly':
            return {}
        
        return {
            'anomaly_type': scenario_metadata.get('anomaly_type'),
            'anomaly_score': scenario_metadata.get('anomaly_score'),
            'detection_confidence': scenario_metadata.get('detection_confidence'),
            'indicators': scenario_metadata.get('anomaly_indicators', []),
            'model_details': {
                'model_type': 'Isolation Forest',
                'training_samples': '100,000+',
                'feature_count': 5,
                'contamination_rate': '10%'
            },
            'recommended_actions': [
                "Require additional authentication",
                "Send verification to registered phone/email",
                "Flag for behavioral analysis review",
                "Monitor subsequent transactions closely"
            ]
        }


# Global scenario engine instance
scenario_engine = ScenarioEngine()
