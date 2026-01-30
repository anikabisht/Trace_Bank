policy = {
    "low_threshold": 30,
    "review_threshold": 60,
    "block_threshold": 85
}

def update_policy(low, review, block):
    policy["low_threshold"] = low
    policy["review_threshold"] = review
    policy["block_threshold"] = block

def decide_action(risk_score):
    if risk_score >= policy["block_threshold"]:
        return "CRITICAL_FRAUD"
    elif risk_score >= policy["review_threshold"]:
        return "BLOCK"
    elif risk_score >= policy["low_threshold"]:
        return "REVIEW"
    else:
        return "APPROVED"
