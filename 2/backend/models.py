from pydantic import BaseModel
from typing import Optional

class Transaction(BaseModel):
    amount: float
    location_distance_km: float
    is_new_device: bool
    hour: int   # 0–23

class Decision(BaseModel):
    transaction_risk: float
    behavioral_risk: float
    final_risk: float
    action: str
    explanation: str