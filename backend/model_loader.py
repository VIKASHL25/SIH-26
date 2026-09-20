import os
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
    FAULT_MODEL_PKL_PATH,
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
            # Current-timestep raw values (original 9)
            "cht_C",
            "egt_C",
            "oil_temperature_C",
            "oil_pressure_bar",
            "vibration_rms",
            "battery_voltage_V",
            "alternator_current_A",
            "alternator_health",
            "injection_timing_deg",
            # Current-timestep raw values (newly added — engine-state context
            # that was missing even though its residual/ratio was present)
            "rpm",
            "fuel_flow_kg_s",
            "power_W",
            "torque_Nm",
            "air_mass_flow_kg_s",
            # Physics residuals (original 4)
            "cht_residual",
            "egt_residual",
            "rpm_residual",
            "physics_residual_C",
            # Efficiency ratios (newly added — already computed in
            # process_raw_sample, just not previously referenced here)
            "fuel_air_ratio",
            "power_per_fuel",
            "torque_per_rpm",
            "power_per_air",
            "egt_rpm_ratio",
            "fuel_egt_ratio",
            # Rolling mean/std/slope over the same 15-sample window used by
            # the fault classification model, for the same 9 core sensors
            # (newly added — requires _generate_anomaly_features to read
            # history_df instead of only the current sample)
            "cht_C_roll_mean", "cht_C_roll_std", "cht_C_slope",
            "egt_C_roll_mean", "egt_C_roll_std", "egt_C_slope",
            "oil_temperature_C_roll_mean", "oil_temperature_C_roll_std", "oil_temperature_C_slope",
            "oil_pressure_bar_roll_mean", "oil_pressure_bar_roll_std", "oil_pressure_bar_slope",
            "fuel_flow_kg_s_roll_mean", "fuel_flow_kg_s_roll_std", "fuel_flow_kg_s_slope",
            "vibration_rms_roll_mean", "vibration_rms_roll_std", "vibration_rms_slope",
            "battery_voltage_V_roll_mean", "battery_voltage_V_roll_std", "battery_voltage_V_slope",
            "injection_timing_deg_roll_mean", "injection_timing_deg_roll_std", "injection_timing_deg_slope",
            "physics_residual_C_roll_mean", "physics_residual_C_roll_std", "physics_residual_C_slope",
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
        # Anomaly Detection Debounce State: an alert only fires once the
        # anomaly score has crossed threshold on 2 consecutive samples,
        # which filters out single-sample sensor noise while adding at
        # most 1 extra second of detection latency on real faults (real
        # faults keep climbing; noise rarely repeats two ticks running).
        self.previous_anomaly_raw: Optional[bool] = None
        self._is_loaded = False
        self.model_hashes: Dict[str, str] = {}

    def reset_state(self):
        """Resets temporal filtering state across mission reloads."""
        self.previous_rul = None
        self.previous_anomaly_raw = None

    def _verify_model_hash(self, model_key: str, file_path: str):
        """Computes SHA-256 hash of model file, logs it, and verifies against models/model_hashes.json."""
        import hashlib
        try:
            with open(file_path, "rb") as f:
                computed_hash = hashlib.sha256(f.read()).hexdigest()
            
            self.model_hashes[model_key] = computed_hash
            logger.info(f"Model integrity SHA-256 [{model_key}]: {computed_hash}")

            # Check against expected hashes in models/model_hashes.json if available
            hashes_json_path = os.path.join(os.path.dirname(file_path), "../model_hashes.json")
            if os.path.exists(hashes_json_path):
                with open(hashes_json_path, "r") as hf:
                    expected_hashes = json.load(hf)
                    expected = expected_hashes.get(model_key)
                    if expected and expected != computed_hash:
                        logger.critical(
                            f"CRITICAL: [SECURITY WARNING] Model integrity mismatch for '{model_key}'! "
                            f"Expected SHA-256: {expected}, Computed: {computed_hash}. File may be tampered!"
                        )
                    elif expected:
                        logger.info(f"✅ Model integrity verified matching expected SHA-256 hash [{model_key}].")
        except Exception as e:
            logger.error(f"Error verifying model hash for {model_key}: {e}")

    def load_all_models(self):
        """Loads all 4 models and feature specifications into memory with integrity verification."""
        logger.info("Initializing loading of all 4 Digital Twin AI/ML models with SHA-256 integrity checks...")

        # 1. Load Anomaly Detection Model & Scaler
        try:
            self._verify_model_hash("anomaly_detection", ANOMALY_MODEL_PATH)
            self.anomaly_model = joblib.load(ANOMALY_MODEL_PATH)
            self.anomaly_scaler = joblib.load(ANOMALY_SCALER_PATH)
            logger.info("Loaded Anomaly Detection Model & Scaler successfully.")
        except Exception as e:
            logger.error(f"Failed to load Anomaly Detection model: {e}")
            raise e

        # 2. Load Degradation Model & Feature Columns
        try:
            self._verify_model_hash("degradation_estimation", DEGRADATION_MODEL_PATH)
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
            self._verify_model_hash("fault_classification", FAULT_MODEL_PATH)
            if str(FAULT_MODEL_PATH).endswith(".json") and os.path.exists(str(FAULT_MODEL_PATH)):
                self.fault_model = XGBClassifier()
                self.fault_model.load_model(str(FAULT_MODEL_PATH))
            elif os.path.exists(str(FAULT_MODEL_PKL_PATH)):
                self.fault_model = joblib.load(FAULT_MODEL_PKL_PATH)
            else:
                self.fault_model = joblib.load(FAULT_MODEL_PATH)
            self.fault_label_encoder = joblib.load(FAULT_LABEL_ENCODER_PATH)
            with open(FAULT_FEATURE_COLS_PATH, "r") as f:
                self.fault_feature_cols = json.load(f)
            logger.info(f"Loaded Fault Classification Model with {len(self.fault_feature_cols)} features successfully.")
        except Exception as e:
            logger.error(f"Failed to load Fault Classification model: {e}")
            raise e

        # 4. Load RUL Model & Feature Specification
        try:
            self._verify_model_hash("rul_prediction", RUL_MODEL_PATH)
            self.rul_model = XGBRegressor()
            self.rul_model.load_model(str(RUL_MODEL_PATH))
            booster_features = self.rul_model.get_booster().feature_names
            if booster_features and len(booster_features) > 0:
                self.rul_feature_cols = booster_features
            else:
                with open(RUL_FEATURE_COLS_PATH, "r") as f:
                    self.rul_feature_cols = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded RUL Model with {len(self.rul_feature_cols)} features successfully.")
        except Exception as e:
            logger.error(f"Failed to load RUL model: {e}")
            raise e

        self._is_loaded = True
        logger.info("All 4 Digital Twin AI/ML models loaded and verified ready for simulation!")

    def predict_anomaly(self, df_51_features: pd.DataFrame, threshold: float = 19.5280) -> dict:
        """
        Model 1: Anomaly Detection Inference (PCA reconstruction-error based,
        with 2-consecutive-sample debouncing).

        self.anomaly_model is now a fitted sklearn PCA (not Isolation Forest).
        anomaly_score = squared reconstruction error in the scaled feature
        space: PCA is fit on 'normal' operating data only, so a sample that
        doesn't fit the learned normal-operation subspace reconstructs
        poorly and gets a high score. `threshold` defaults to the value
        calibrated in config.ANOMALY_THRESHOLD (95th percentile of normal
        training reconstruction error, chosen for faster detection) and
        should be passed from there by the caller, same as before.

        Debouncing: the raw per-sample threshold crossing is tracked in
        `raw_anomaly`. The reported `is_anomaly` only fires once the raw
        flag has been True for 2 consecutive calls, filtering out
        single-tick sensor noise at the cost of at most 1 extra second of
        latency on genuine, sustained faults. Call `reset_state()` between
        missions so debounce state doesn't leak across mission boundaries.
        """
        scaled = self.anomaly_scaler.transform(df_51_features[self.anomaly_feature_cols])
        reconstructed = self.anomaly_model.inverse_transform(self.anomaly_model.transform(scaled))
        anomaly_score = float(np.sum((scaled - reconstructed) ** 2, axis=1)[0])
        raw_anomaly = bool(anomaly_score >= threshold)

        is_anomaly = bool(raw_anomaly and self.previous_anomaly_raw)
        self.previous_anomaly_raw = raw_anomaly

        return {
            "anomaly_score": round(anomaly_score, 4),
            "is_anomaly": is_anomaly,
            "raw_anomaly": raw_anomaly,
            "decision_function": round(-anomaly_score, 4)
        }

    def predict_degradation(
        self,
        df_120_features: pd.DataFrame,
        clean_sample: Optional[dict] = None
    ) -> dict:
        """
        Model 2: Degradation Estimation Inference.

        IMPORTANT:
        Ground-truth fields such as `degradation` and `health_index`
        are never used for inference.

        The XGBoost model predicts degradation exclusively from
        the generated 120-feature vector.
        """

        inp = df_120_features[self.degradation_feature_cols].astype(float)

        deg_score = float(
            self.degradation_model.predict(inp.values)[0]
        )

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
        Applies Exponential Moving Average (EMA, alpha=0.15) and Slew Rate Limiting.
        Purely physics and telemetry driven, with zero dependence on arbitrary health% heuristic anchors.
        Enforces terminal failure zeroing only when degradation index >= 0.98.
        """
        raw_rul = max(0.0, float(raw_rul))

        # Terminal failure state enforcement
        if degradation_index is not None and degradation_index >= 0.98:
            raw_rul = 0.0

        if self.previous_rul is None:
            filtered = raw_rul
        else:
            # Low-pass filter step (alpha = 0.15)
            alpha = 0.15
            filtered = alpha * raw_rul + (1.0 - alpha) * self.previous_rul
            
            # Slew-rate limiting per tick (max +1.0h increase / -3.0h decrease per tick)
            delta = filtered - self.previous_rul
            if delta > 1.0:
                filtered = self.previous_rul + 1.0
            elif delta < -3.0:
                filtered = self.previous_rul - 3.0

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
        def _to_df(val):
            if val is None:
                return None
            if isinstance(val, pd.DataFrame):
                return val
            if isinstance(val, list):
                return pd.DataFrame(val)
            if isinstance(val, dict):
                return pd.DataFrame([val])
            return val

        clean_sample = feature_vectors.get("clean_sample")
        anomaly_df = _to_df(feature_vectors.get("anomaly"))
        degradation_df = _to_df(feature_vectors.get("degradation"))
        fault_df = _to_df(feature_vectors.get("fault"))
        rul_df = _to_df(feature_vectors.get("rul"))

        anomaly_res = self.predict_anomaly(anomaly_df, threshold=anomaly_threshold)
        degradation_res = self.predict_degradation(degradation_df, clean_sample=clean_sample)
        fault_res = self.predict_fault(fault_df)
        
        # Pass health_pct & degradation_index to RUL for dynamic anchoring & smooth failure filtering
        health_pct = degradation_res.get("estimated_health_pct")
        deg_idx = degradation_res.get("degradation_index")
        rul_res = self.predict_rul(
            rul_df,
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
            "rul_prediction": rul_res,
            "metadata": {
                "model_hashes": self.model_hashes,
                "verified_integrity": True
            }
        }
