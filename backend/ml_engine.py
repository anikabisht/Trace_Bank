
import os
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "models")
DATA_FILE = os.path.join(DATA_DIR, "training_data.csv")
MODEL_FILE = os.path.join(MODEL_DIR, "risk_model.pkl")

class ContinuousMLEngine:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(MODEL_DIR, exist_ok=True)

        self.model = RandomForestClassifier(n_estimators=150, random_state=42)
        self.is_trained = False

        self.load_model()
        self.ensure_cold_start_model()

    def load_model(self):
        if os.path.exists(MODEL_FILE):
            try:
                self.model = joblib.load(MODEL_FILE)
                self.is_trained = True
                print("✅ ML model loaded from disk")
            except Exception as e:
                print("⚠️ Model load failed:", e)

    def save_model(self):
        joblib.dump(self.model, MODEL_FILE)
        print("💾 ML model saved")

    def ensure_cold_start_model(self):
        try:
            self.model.predict_proba(pd.DataFrame([self.default_features()]))
            self.is_trained = True
        except Exception:
            print("⚠️ Cold start: training base ML model...")

            X = pd.DataFrame([
                {"amount": 100, "velocity": 0, "location_risk": 0, "behavior_score": 0},
                {"amount": 500, "velocity": 1, "location_risk": 0, "behavior_score": 1},
                {"amount": 20000, "velocity": 6, "location_risk": 4, "behavior_score": 7},
                {"amount": 50000, "velocity": 10, "location_risk": 8, "behavior_score": 9},
            ])
            y = [0, 0, 1, 1]

            self.model.fit(X, y)
            self.is_trained = True
            self.save_model()

            print("✅ Base ML model trained")

    def default_features(self):
        return {"amount": 100, "velocity": 0, "location_risk": 0, "behavior_score": 0}

    def save_transaction(self, features, label):
        row = {**features, "label": label}

        if os.path.exists(DATA_FILE):
            df = pd.read_csv(DATA_FILE)
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        else:
            df = pd.DataFrame([row])

        df.to_csv(DATA_FILE, index=False)

        if len(df) >= 10 and len(df) % 10 == 0:
            self.retrain_model(df)

    def retrain_model(self, df=None):
        if df is None:
            if not os.path.exists(DATA_FILE):
                return
            df = pd.read_csv(DATA_FILE)

        if len(df) < 5:
            return

        X = df.drop("label", axis=1)
        y = df["label"]

        self.model.fit(X, y)
        self.is_trained = True
        self.save_model()

        print(f"🔄 ML retrained with {len(df)} samples")

    def predict(self, features):
        X = pd.DataFrame([features])

        if not self.is_trained:
            return "APPROVE", 0.1

        try:
            risk_score = self.model.predict_proba(X)[0][1]
        except Exception as e:
            print("⚠️ ML prediction error:", e)
            return "APPROVE", 0.1

        if risk_score > 0.75:
            decision = "BLOCK"
        elif risk_score > 0.45:
            decision = "REVIEW"
        else:
            decision = "APPROVE"

        return decision, round(float(risk_score), 3)
    
    def detect_vpn(self, ip_address=None, location=None):
        """
        Fake VPN detection (placeholder logic).
        Returns probability between 0 and 1.
        """
        # if ip_address is None:
        #     return 0.1
        return 0.2  # simple heuristic (you can improve later)

    def detect_proxy(self, ip_address=None):
        """
        Fake proxy detection.
        """
        if ip_address is None:
            return 0.1
        return 0.15

    def analyze_behavior(self, behavior_data=None):
        """
        Behavior risk score (0–1).
        """
        if behavior_data is None:
            return 0.3
        score = min(1.0, max(0.0, len(str(behavior_data)) / 100))
        reasons = ["behavior_pattern_checked"]

        return score, reasons

    def detect_fraud_ring(self, user_id=None, device_id=None):
        """
        Fraud ring probability.
        """
        return 0.05  # default low risk

# ================= LEGACY COMPATIBILITY FUNCTIONS =================
# Some parts of app.py expect these functions from older ML engine versions.

def calculate_behavior_score(behavior_data=None):
        """Fallback behavior score for compatibility."""
        if behavior_data is None:
            return 0.5
        try:
            return min(1.0, max(0.0, float(len(str(behavior_data))) / 100))
        except:
            return 0.5

       