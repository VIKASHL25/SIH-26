import os
from pathlib import Path

# Workspace Root Directory (Parent of backend folder)
BASE_DIR = Path(__file__).resolve().parent.parent

# Model Paths
ANOMALY_MODEL_PATH = BASE_DIR / "models" / "anomaly_detection" / "isolation_forest_model.pkl"
ANOMALY_SCALER_PATH = BASE_DIR / "models" / "anomaly_detection" / "scaler.pkl"

DEGRADATION_MODEL_PATH = BASE_DIR / "models" / "degradation_detection" / "xgb_degradation_model.json"
DEGRADATION_FEATURE_COLS_PATH = BASE_DIR / "models" / "degradation_detection" / "feature_columns.json"

FAULT_MODEL_PATH = BASE_DIR / "models" / "fault_detection" / "fault_detection_multiclass_xgb.pkl"
FAULT_LABEL_ENCODER_PATH = BASE_DIR / "models" / "fault_detection" / "fault_detection_label_encoder.pkl"
FAULT_FEATURE_COLS_PATH = BASE_DIR / "models" / "fault_detection" / "fault_detection_multiclass_feature_cols.json"

RUL_MODEL_PATH = BASE_DIR / "models" / "rul_prediction" / "xgboost_rul_model.json"
RUL_FEATURE_COLS_PATH = BASE_DIR / "models" / "rul_prediction" / "xgboost_rul_features.txt"

# Dataset Paths
DATASET_100K_PATH = BASE_DIR / "data" / "MALE_UAV_aero_piston_engine_final_100k.csv"
DATASET_RUL_PATH = BASE_DIR / "data" / "aero_piston_RUL_300_engines.csv"

# Backend Server Configuration
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000

# Anomaly Detection Settings
ANOMALY_THRESHOLD = 0.0  # decision function output threshold convention (-decision_function >= threshold)

# Default Fallback Values for Sensor Inputs
DEFAULT_SENSOR_DEFAULTS = {
    "altitude_m": 1000.0,
    "ambient_temp_C": 25.0,
    "pressure_kPa": 101.325,
    "air_density_kg_m3": 1.225,
    "throttle_pct": 70.0,
    "load_pct": 70.0,
    "rpm": 2300.0,
    "air_mass_flow_kg_s": 0.08,
    "fuel_flow_kg_s": 0.005,
    "torque_Nm": 150.0,
    "power_W": 36000.0,
    "cht_C": 135.0,
    "egt_C": 670.0,
    "oil_temperature_C": 85.0,
    "oil_pressure_bar": 4.5,
    "vibration_rms": 0.15,
    "battery_voltage_V": 28.0,
    "alternator_current_A": 25.0,
    "alternator_health": 1.0,
    "injection_timing_deg": 15.0,
    "expected_rpm": 2300.0,
    "expected_cht_C": 135.0,
    "expected_egt_C": 670.0,
    "physics_residual_C": 0.0
}
