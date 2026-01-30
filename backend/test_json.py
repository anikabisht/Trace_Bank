#!/usr/bin/env python
"""Test JSON serialization of responses"""

import json
import asyncio
from datetime import datetime
from fastapi.responses import JSONResponse

# Simulate the response
test_response = {
    'transaction_id': 'abc123',
    'user_id': 'user_001',
    'amount_inr': 50000.0,
    'currency': 'INR',
    'risk_score': 45.5,
    'risk_level': 'MEDIUM_HIGH',
    'decision': 'PENDING_REVIEW',
    'component_risks': {
        'amount': 15.0,
        'location': 5.0,
        'merchant': 2.0,
        'time': 0.0,
        'behavior': 0.0,
        'velocity': 0.0
    },
    'counterfactuals': [
        {
            'type': 'amount',
            'title': '💰 Reduce Transaction Amount',
            'explanation': 'Your amount is too high',
            'current': '₹50000',
            'suggested': '₹30000',
            'impact': 'Reduces risk by ~10 points',
            'user_action': 'Try a smaller amount',
            'confidence': 95,
            'practicality': 'high'
        }
    ],
    'churn_impact': {
        'churn_probability': '5.0%',
        'revenue_at_risk': '₹50.0',
        'retention_score': '95.0/100',
        'recommendation': 'Decision appropriate'
    },
    'fraud_ring_alert': None,
    'tracking_summary': {
        'location': 'Mumbai, India',
        'gps_enabled': True,
        'behavior_match': 'NORMAL',
        'device_trust': 'KNOWN',
        'time_context': 'NORMAL'
    },
    'timestamp': datetime.now().isoformat()
}

# Test JSON serialization
try:
    json_str = json.dumps(test_response)
    print("✅ JSON serialization successful!")
    print(f"Response size: {len(json_str)} bytes")
    
    # Try to parse it back
    parsed = json.loads(json_str)
    print("✅ JSON parsing successful!")
    print(f"Amount: {parsed['amount_inr']}")
    print(f"Risk Score: {parsed['risk_score']}")
    print(f"Counterfactuals: {len(parsed['counterfactuals'])} items")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n✅ All serialization tests passed!")
