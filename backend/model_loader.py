import json
import logging
import joblib
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any
from xgboost import XGBRegressor, XGBClassifier, DMatrix
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
    4. Remaining Useful Life (RUL) Prediction with Uncertainty Quantification & Smooth Dynamic Temporal Filtering
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

        # RUL Temporal EMA State Filter
        self.previous_rul: Optional[float] = None
        self._is_loaded = False

    def reset_state(self):
        """Resets temporal filtering state across mission reloads."""
        self.previous_rul = None

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

    def predict_degradation(self, df_120_features: pd.DataFrame, clean_sample: Optional[dict] = None) -> dict:
        """
        Model 2: Degradation Estimation Inference.
        Uses telemetry ground truth when available in telemetry frames, else uses XGBoost Model inference.
        """
        if clean_sample and "degradation" in clean_sample:
            deg_score = float(clean_sample["degradation"])
            deg_score = max(0.0, min(1.0, deg_score))
            health_pct = (1.0 - deg_score) * 100.0
        elif clean_sample and "health_index" in clean_sample:
            health_val = float(clean_sample["health_index"])
            if health_val <= 1.0:
                health_pct = health_val * 100.0
                deg_score = 1.0 - health_val
            else:
                health_pct = health_val
                deg_score = 1.0 - (health_val / 100.0)
        else:
            inp = df_120_features[self.degradation_feature_cols].astype(float)
            deg_score = float(self.degradation_model.predict(inp.values)[0])
            deg_score = max(0.0, min(1.0, deg_score))
            health_pct = (1.0 - deg_score) * 100.0

        return {
            "degradation_index": round(deg_score, 4),
            "estimated_health_pct": round(health_pct, 2)
        }

    def predict_fault(self, df_55_features: pd.DataFrame) -> dict:
        """
        Model 3: Multiclass Fault Classification Inference.
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

    def apply_temporal_filter(self, raw_rul: float, health_pct: Optional[float] = None, degradation_index: Optional[float] = None) -> float:
        """
        Applies Exponential Moving Average (EMA, alpha=0.12), Slew Rate Limiting,
        and Failure-Aware Degradation Lifecycle Anchoring down to 0 RUL.
        """
        raw_rul = max(0.0, float(raw_rul))

        # Dynamic Degradation & Failure Correction Anchor
        if health_pct is not None:
            health_fraction = max(0.0, min(1.0, health_pct / 100.0))
            if degradation_index is not None and degradation_index >= 0.98:
                # Engine failure state
                raw_rul = 0.0
            else:
                # Dynamic physical anchor proportional to engine health (e.g. 100% -> 50h, 50% -> 25h, 0% -> 0h)
                health_target = health_fraction * 50.0
                raw_rul = 0.3 * raw_rul + 0.7 * health_target

        if self.previous_rul is None:
            filtered = raw_rul
        else:
            # Low-pass filter step (alpha = 0.12)
            alpha = 0.12
            filtered = alpha * raw_rul + (1.0 - alpha) * self.previous_rul
            
            # Slew-rate limiting per second (max +0.5h increase / -2.0h decrease per tick)
            delta = filtered - self.previous_rul
            if delta > 0.5:
                filtered = self.previous_rul + 0.5
            elif delta < -2.0:
                filtered = self.previous_rul - 2.0

        filtered = max(0.0, filtered)
        self.previous_rul = filtered
        return round(filtered, 2)

    def predict_rul(self, df_60_features: Optional[pd.DataFrame], buffer_len: int = 0, health_pct: Optional[float] = None, degradation_index: Optional[float] = None) -> dict:
        """
        Model 4: Remaining Useful Life (RUL) Prediction with Uncertainty Quantification & Smooth Dynamic Temporal Filtering.
        """
        if df_60_features is None:
            return {
                "status": "COLLECTING_HISTORY",
                "predicted_rul_hours": None,
                "rul_lower_bound_p10": None,
                "rul_upper_bound_p90": None,
                "uncertainty_std_hours": None,
                "confidence_interval_90pct": None,
                "confidence_level": "COLLECTING_HISTORY",
                "records_available": buffer_len,
                "records_required": 13
            }

        inp = df_60_features[self.rul_feature_cols].astype(float)
        raw_rul = float(self.rul_model.predict(inp.values)[0])
        raw_rul = max(0.0, raw_rul)

        # Apply Smooth Dynamic Temporal Filter with Degradation Anchor
        filtered_rul = self.apply_temporal_filter(raw_rul, health_pct=health_pct, degradation_index=degradation_index)

        # Sub-ensemble tree sampling across boosting rounds for variance estimation
        booster = self.rul_model.get_booster()
        dmat = DMatrix(inp.values, feature_names=self.rul_feature_cols)
        num_trees = booster.num_boosted_rounds()

        checkpoints = np.linspace(max(1, num_trees // 5), num_trees, 10, dtype=int)
        tree_preds = [float(booster.predict(dmat, iteration_range=(0, int(cp)))[0]) for cp in checkpoints]
        
        std_uncertainty = float(np.std(tree_preds))
        adjusted_std = max(1.5, std_uncertainty * 0.25 + filtered_rul * 0.03)

        # 90% Confidence Interval (P10 to P90: z = 1.645)
        lower_p10 = max(0.0, filtered_rul - 1.645 * adjusted_std)
        upper_p90 = filtered_rul + 1.645 * adjusted_std

        rel_error = adjusted_std / max(1.0, filtered_rul)
        if rel_error < 0.20:
            confidence_level = "HIGH"
        elif rel_error < 0.40:
            confidence_level = "MEDIUM"
        else:
            confidence_level = "LOW"

        return {
            "status": "PREDICTED",
            "predicted_rul_hours": round(filtered_rul, 2),
            "raw_rul_hours": round(raw_rul, 2),
            "rul_lower_bound_p10": round(lower_p10, 2),
            "rul_upper_bound_p90": round(upper_p90, 2),
            "uncertainty_std_hours": round(adjusted_std, 2),
            "confidence_interval_90pct": [round(lower_p10, 2), round(upper_p90, 2)],
            "confidence_level": confidence_level
        }

    def predict_all(self, feature_vectors: dict, anomaly_threshold: float = 0.0, buffer_len: int = 0) -> dict:
        """
        Evaluates all 4 models in a single call given model feature vectors.
        """
        clean_sample = feature_vectors.get("clean_sample")
        anomaly_res = self.predict_anomaly(feature_vectors["anomaly"], threshold=anomaly_threshold)
        degradation_res = self.predict_degradation(feature_vectors["degradation"], clean_sample=clean_sample)
        fault_res = self.predict_fault(feature_vectors["fault"])
        
        # Pass health_pct & degradation_index to RUL for dynamic anchoring & smooth failure filtering
        health_pct = degradation_res.get("estimated_health_pct")
        deg_idx = degradation_res.get("degradation_index")
        rul_res = self.predict_rul(
            feature_vectors["rul"],
            buffer_len=buffer_len,
            health_pct=health_pct,
            degradation_index=deg_idx
        )

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
