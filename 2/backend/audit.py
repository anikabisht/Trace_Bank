AUDIT_LOG = []

def log_decision(tx, decision):
    AUDIT_LOG.append({
        "transaction": tx.dict(),
        "decision": decision.dict()
    })

def get_audit_log():
    return AUDIT_LOG
