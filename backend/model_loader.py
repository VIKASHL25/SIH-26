import json
import logging
import joblib
import pandas as pd
from xgboost import XGBRegressor, XGBClassifier
from backend.config import (
    ANOMALY_MODEL_PATH,
    ANOMALY_SCALER_PATH,
    DEGRADATION_MODEL_PATH,
    DEGRADATION_FEATURE_COLS_PATH,
    FAULT_MODEL_PATH,
    FAULT_LABEL_ENCODER_PATH,
    FAULT_FEATURE_COLS_PATH,
    RUL_MODEL_PATH,
    RUL_FEATURE_COLS_PATH,
)

logger = logging.getLogger("DigitalTwinModelManager")

class DigitalTwinModelManager:
    """
    Unified Manager for loading, managing, and performing inference on all 4 Digital Twin AI/ML models:
    1. Anomaly Detection (Isolation Forest + Scaler)
    2. Degradation Estimation (XGBoost Regressor)
    3. Fault Classification (Multiclass XGBoost Classifier + Label Encoder)
    4. Remaining Useful Life (RUL) Prediction (XGBoost Regressor)
    """

    def __init__(self):
        self.anomaly_model = None
        self.anomaly_scaler = None
        self.anomaly_feature_cols = [
            "cht_C",
            "egt_C",
            "oil_temperature_C",
            "oil_pressure_bar",
            "vibration_rms",
            "battery_voltage_V",
            "alternator_current_A",
            "alternator_health",
            "injection_timing_deg",
            "cht_residual",
            "egt_residual",
            "rpm_residual",
            "physics_residual_C",
        ]

        self.degradation_model = None
        self.degradation_feature_cols = []

        self.fault_model = None
        self.fault_label_encoder = None
        self.fault_feature_cols = []

        self.rul_model = None
        self.rul_feature_cols = []

        self._is_loaded = False

    def load_all_models(self):
        """Loads all 4 models and feature specifications into memory."""
        logger.info("Initializing loading of all 4 Digital Twin AI/ML models...")

        # 1. Load Anomaly Detection Model & Scaler
        try:
            self.anomaly_model = joblib.load(ANOMALY_MODEL_PATH)
            self.anomaly_scaler = joblib.load(ANOMALY_SCALER_PATH)
            logger.info("Loaded Anomaly Detection Model & Scaler successfully.")
        except Exception as e:
            logger.error(f"Failed to load Anomaly Detection model: {e}")
            raise e

        # 2. Load Degradation Model & Feature Columns
        try:
            self.degradation_model = XGBRegressor()
            self.degradation_model.load_model(str(DEGRADATION_MODEL_PATH))
            with open(DEGRADATION_FEATURE_COLS_PATH, "r") as f:
                self.degradation_feature_cols = json.load(f)
            logger.info(f"Loaded Degradation XGBoost Model with {len(self.degradation_feature_cols)} features successfully.")
        except Exception as e:
            logger.error(f"Failed to load Degradation model: {e}")
            raise e

        # 3. Load Fault Classification Model & Label Encoder
        try:
            self.fault_model = joblib.load(FAULT_MODEL_PATH)
            self.fault_label_encoder = joblib.load(FAULT_LABEL_ENCODER_PATH)
            with open(FAULT_FEATURE_COLS_PATH, "r") as f:
                self.fault_feature_cols = json.load(f)
            logger.info(f"Loaded Fault Classification Model with {len(self.fault_feature_cols)} features successfully.")
        except Exception as e:
            logger.error(f"Failed to load Fault Classification model: {e}")
            raise e

        # 4. Load RUL Model & Feature Columns
        try:
            self.rul_model = XGBRegressor()
            self.rul_model.load_model(str(RUL_MODEL_PATH))
            booster_features = self.rul_model.get_booster().feature_names
            if booster_features:
                self.rul_feature_cols = list(booster_features)
            else:
                with open(RUL_FEATURE_COLS_PATH, "r") as f:
                    self.rul_feature_cols = [line.strip() for line in f.readlines() if line.strip()]
            logger.info(f"Loaded RUL Model with {len(self.rul_feature_cols)} features successfully.")
        except Exception as e:
            logger.error(f"Failed to load RUL model: {e}")
            raise e

        self._is_loaded = True
        logger.info("All 4 Digital Twin AI/ML models loaded and ready for simulation!")

    def predict_anomaly(self, df_13_features: pd.DataFrame, threshold: float = 0.0) -> dict:
        """
        Model 1: Anomaly Detection Inference.
        Returns anomaly_score (higher = more anomalous) and binary prediction flag.
        """
        scaled = self.anomaly_scaler.transform(df_13_features[self.anomaly_feature_cols])
        decision_val = float(self.anomaly_model.decision_function(scaled)[0])
        anomaly_score = -decision_val
        is_anomaly = bool(anomaly_score >= threshold)
        return {
            "anomaly_score": round(anomaly_score, 4),
            "is_anomaly": is_anomaly,
            "decision_function": round(decision_val, 4)
        }

    def predict_degradation(self, df_120_features: pd.DataFrame) -> dict:
        """
        Model 2: Degradation Estimation Inference.
        Returns degradation level (0.0 to 1.0) and estimated health percentage.
        """
        inp = df_120_features[self.degradation_feature_cols].astype(float)
        deg_score = float(self.degradation_model.predict(inp.values)[0])
        deg_score = max(0.0, min(1.0, deg_score))
        health_pct = round((1.0 - deg_score) * 100.0, 2)
        return {
            "degradation_index": round(deg_score, 4),
            "estimated_health_pct": health_pct
        }

    def predict_fault(self, df_55_features: pd.DataFrame) -> dict:
        """
        Model 3: Multiclass Fault Classification Inference.
        Returns predicted fault label and probability distribution across fault types.
        """
        inp = df_55_features[self.fault_feature_cols].astype(float)
        probs = self.fault_model.predict_proba(inp)[0]
        pred_idx = probs.argmax()
        fault_label = self.fault_label_encoder.inverse_transform([pred_idx])[0]
        classes = self.fault_label_encoder.classes_
        class_probabilities = {str(c): round(float(p), 4) for c, p in zip(classes, probs)}
        
        return {
            "predicted_fault": str(fault_label),
            "confidence": round(float(probs[pred_idx]), 4),
            "fault_probabilities": class_probabilities
        }

    def predict_rul(self, df_60_features: pd.DataFrame) -> dict:
        """
        Model 4: Remaining Useful Life (RUL) Prediction Inference.
        Returns predicted RUL in flight hours.
        """
        inp = df_60_features[self.rul_feature_cols].astype(float)
        predicted_rul = float(self.rul_model.predict(inp.values)[0])
        predicted_rul = max(0.0, predicted_rul)
        return {
            "predicted_rul_hours": round(predicted_rul, 2)
        }

    def predict_all(self, feature_vectors: dict, anomaly_threshold: float = 0.0) -> dict:
        """
        Evaluates all 4 models in a single call given model feature vectors.
        """
        anomaly_res = self.predict_anomaly(feature_vectors["anomaly"], threshold=anomaly_threshold)
        degradation_res = self.predict_degradation(feature_vectors["degradation"])
        fault_res = self.predict_fault(feature_vectors["fault"])
        rul_res = self.predict_rul(feature_vectors["rul"])

        if anomaly_res["is_anomaly"]:
            status = "ANOMALOUS / WARNING"
        elif fault_res["predicted_fault"] != "normal":
            status = f"FAULT DETECTED ({fault_res['predicted_fault'].upper()})"
        else:
            status = "NOMINAL"

        return {
            "status": status,
            "anomaly_detection": anomaly_res,
            "degradation_estimation": degradation_res,
            "fault_classification": fault_res,
            "rul_prediction": rul_res
        }
