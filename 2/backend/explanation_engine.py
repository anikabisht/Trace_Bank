def generate_explanation(tx, final_risk, action):
    reasons = []

    if tx.amount > 5000:
        reasons.append("High transaction amount")

    if tx.location_distance_km > 100:
        reasons.append("Transaction from distant location")

    if tx.is_new_device:
        reasons.append("New device detected")

    if tx.hour < 6 or tx.hour > 22:
        reasons.append("Unusual transaction time")

    reason_text = ", ".join(reasons) if reasons else "Normal behavior"

    return f"Decision: {action}. Risk Score: {final_risk}. Reasons: {reason_text}"

def generate_explanation(decision_data):
    explanation = {
        "final_decision": decision_data["decision"],
        "risk_breakdown": {
            "transaction_risk": decision_data["txn_risk"],
            "behavioural_risk": decision_data["behavioural_risk"],
            "fraud_ring_risk": decision_data["fraud_ring_risk"]
        },
        "key_reasons": decision_data["reasons"]
    }

    return explanation