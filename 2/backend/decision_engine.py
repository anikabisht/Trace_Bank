
from datetime import datetime

BLOCK_THRESHOLD = 80
REVIEW_THRESHOLD = 50

def update_policy(block_threshold=None, review_threshold=None):
    global BLOCK_THRESHOLD, REVIEW_THRESHOLD
    if block_threshold is not None:
        BLOCK_THRESHOLD = block_threshold
    if review_threshold is not None:
        REVIEW_THRESHOLD = review_threshold
    return {"block_threshold": BLOCK_THRESHOLD, "review_threshold": REVIEW_THRESHOLD}

def make_decision(score):
    if score >= BLOCK_THRESHOLD:
        return "BLOCK", "High risk transaction"
    elif score >= REVIEW_THRESHOLD:
        return "REVIEW", "Needs manual review"
    elif score >= 90:
        return "FRAUD", "Fraud pattern detected"
    else:
        return "APPROVED", "Low risk transaction"

def calculate_final_risk(txn_risk, behavioural_risk, fraud_ring_risk):
    return round(
        0.4 * txn_risk +
        0.3 * behavioural_risk +
        0.3 * fraud_ring_risk,
        2
    )