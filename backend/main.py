from fastapi import Body
from fastapi import FastAPI
from models import Transaction, Decision
from risk_engine import (
    calculate_transaction_risk,
    calculate_behavioral_risk,
    calculate_final_risk
)
from policy_engine import decide_action, update_policy
from explanation_engine import generate_explanation
from audit import log_decision, get_audit_log

app = FastAPI(title="Explainable Banking Decision Engine")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/simulate", response_model=Decision)
def simulate_transaction(tx: Transaction):
    tr = calculate_transaction_risk(tx)
    br = calculate_behavioral_risk()
    fr = calculate_final_risk(tr, br)

    action = decide_action(fr)
    explanation = generate_explanation(tx, fr, action)

    decision = Decision(
        transaction_risk=tr,
        behavioral_risk=br,
        final_risk=fr,
        action=action,
        explanation=explanation
    )

    log_decision(tx, decision)
    return decision

from fastapi import Body
@app.post("/evaluate")
def evaluate(txn: dict = Body(...)):
    risk_score = 0
    reasons = []

    if txn.get("amount", 0) > 50000:
        risk_score += 30
        reasons.append("High transaction amount")

    if txn.get("velocity_24h", 0) > 5:
        risk_score += 25
        reasons.append("High transaction frequency")

    if txn.get("otp_failures", 0) > 2:
        risk_score += 20
        reasons.append("Multiple OTP failures")

    if txn.get("tenure_months", 0) < 3:
        risk_score += 15
        reasons.append("New customer")

    return {
        "risk_score": risk_score,
        "reasons": reasons
    }

from fastapi import Body
@app.post("/policy/update")
def change_policy(data: dict = Body(...)):
    low = data.get("low_threshold")
    review = data.get("review_threshold")
    block = data.get("block_threshold")

    update_policy(low, review, block)

    return {
        "message": "Policy updated successfully",
        "policy": {
            "low": low,
            "review": review,
            "block": block
        }
    }



audit_logs = []

@app.post("/audit")
def save_audit(data: dict):
    audit_logs.append(data)
    return {
        "message": "Audit saved successfully",
        "total_logs": len(audit_logs)
    }

@app.get("/audit")
def view_audit_log():
    return audit_logs
