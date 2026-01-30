
import pandas as pd
from ml_engine import ContinuousMLEngine

engine = ContinuousMLEngine()

df = pd.read_csv("data/training_data.csv")

X = df.drop("label", axis=1)
y = df["label"]

engine.model.fit(X, y)
engine.save_model()

print("✅ ML model trained manually with CSV data")
