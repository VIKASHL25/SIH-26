import sys, os
sys.path.insert(0, os.path.abspath("."))
import pandas as pd
import numpy as np
import joblib
from backend.config import ANOMALY_MODEL_PATH, ANOMALY_SCALER_PATH

scaler = joblib.load(ANOMALY_SCALER_PATH)
model = joblib.load(ANOMALY_MODEL_PATH)

cols = [
    "cht_C", "egt_C", "oil_temperature_C", "oil_pressure_bar", "vibration_rms",
    "battery_voltage_V", "alternator_current_A", "alternator_health",
    "injection_timing_deg", "cht_residual", "egt_residual", "rpm_residual", "physics_residual_C"
]

df_100k = pd.read_csv("data/MALE_UAV_aero_piston_engine_final_100k.csv")
print("100k Dataset Shape:", df_100k.shape)

# Check normal rows in 100k
normal_100k = df_100k[df_100k.get("fault_type", "normal") == "normal"].copy()
if "cht_residual" not in normal_100k.columns and "expected_cht_C" in normal_100k.columns:
    normal_100k["cht_residual"] = normal_100k["cht_C"] - normal_100k["expected_cht_C"]
if "egt_residual" not in normal_100k.columns and "expected_egt_C" in normal_100k.columns:
    normal_100k["egt_residual"] = normal_100k["egt_C"] - normal_100k["expected_egt_C"]
if "rpm_residual" not in normal_100k.columns and "expected_rpm" in normal_100k.columns:
    normal_100k["rpm_residual"] = normal_100k["rpm"] - normal_100k["expected_rpm"]

print("\n--- 100k NORMAL DATASET STATS ---")
print(normal_100k[cols].describe().T[["mean", "std", "min", "max"]])

df_demo = pd.read_csv("data/demo_synthetic_flight_test.csv")
if "alternator_health" not in df_demo.columns:
    df_demo["alternator_health"] = 1.0
if "cht_residual" not in df_demo.columns and "expected_cht_C" in df_demo.columns:
    df_demo["cht_residual"] = df_demo["cht_C"] - df_demo["expected_cht_C"]
if "egt_residual" not in df_demo.columns and "expected_egt_C" in df_demo.columns:
    df_demo["egt_residual"] = df_demo["egt_C"] - df_demo["expected_egt_C"]
if "rpm_residual" not in df_demo.columns and "expected_rpm" in df_demo.columns:
    df_demo["rpm_residual"] = df_demo["rpm"] - df_demo["expected_rpm"]

print("\n--- DEMO 999 DATASET STATS (First 100 frames) ---")
print(df_demo[cols].head(100).describe().T[["mean", "std", "min", "max"]])

# Test Anomaly on 100k normal sample
scaled_100k = scaler.transform(normal_100k[cols].head(20))
dec_100k = model.decision_function(scaled_100k)
print("\n100k Normal Decisions (positive=inlier, negative=anomaly):", dec_100k[:10])

# Test Anomaly on Demo 999
scaled_demo = scaler.transform(df_demo[cols].head(20))
dec_demo = model.decision_function(scaled_demo)
print("\nDemo 999 Decisions (positive=inlier, negative=anomaly):", dec_demo[:10])
