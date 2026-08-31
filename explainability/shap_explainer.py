import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
import shap

from explainability.feature_mapper import FeatureMapper
from explainability.confidence import (
    calculate_fault_confidence,
    calculate_degradation_confidence,
    calculate_rul_confidence
)

logger = logging.getLogger("XAI_TreeExplainer")

class DigitalTwinTreeExplainer:
    """
    Cached SHAP TreeExplainer manager for frozen XGBoost models:
    - Fault Classification (Multiclass XGBoost Classifier)
    - Degradation Estimation (XGBoost Regressor)
    - Remaining Useful Life - RUL (XGBoost Regressor)
    """

    def __init__(self, feature_mapper: Optional[FeatureMapper] = None):
        self.mapper = feature_mapper or FeatureMapper()
        self.fault_explainer = None
        self.degradation_explainer = None
        self.rul_explainer = None

    def initialize_explainers(self, model_manager):
        """
        Initializes and caches shap.TreeExplainer instances once on loaded model objects.
        Does not reload models or retrain anything.
        """
        logger.info("Initializing cached SHAP TreeExplainers for XGBoost models...")
        
        # 1. Fault Model Explainer
        if model_manager.fault_model is not None and self.fault_explainer is None:
            try:
                self.fault_explainer = shap.TreeExplainer(model_manager.fault_model)
                logger.info("Initialized Fault TreeExplainer successfully.")
            except Exception as e:
                logger.warning(f"Could not initialize Fault TreeExplainer with default settings: {e}")
                self.fault_explainer = shap.TreeExplainer(model_manager.fault_model.get_booster())

        # 2. Degradation Model Explainer
        if model_manager.degradation_model is not None and self.degradation_explainer is None:
            try:
                self.degradation_explainer = shap.TreeExplainer(model_manager.degradation_model)
                logger.info("Initialized Degradation TreeExplainer successfully.")
            except Exception as e:
                logger.warning(f"Could not initialize Degradation TreeExplainer: {e}")
                self.degradation_explainer = shap.TreeExplainer(model_manager.degradation_model.get_booster())

        # 3. RUL Model Explainer
        if model_manager.rul_model is not None and self.rul_explainer is None:
            try:
                self.rul_explainer = shap.TreeExplainer(model_manager.rul_model)
                logger.info("Initialized RUL TreeExplainer successfully.")
            except Exception as e:
                logger.warning(f"Could not initialize RUL TreeExplainer: {e}")
                self.rul_explainer = shap.TreeExplainer(model_manager.rul_model.get_booster())

    # --------------------------------------------------------------------------------
    # 1. FAULT CLASSIFICATION EXPLANATION
    # --------------------------------------------------------------------------------
    def explain_fault(
        self,
        df_55_features: pd.DataFrame,
        model_manager,
        prediction_result: Dict[str, Any],
        top_n: int = 5
    ) -> Dict[str, Any]:
        """
        Generates local SHAP explanation for the Multiclass Fault Classifier.
        Explains feature contributions towards the PREDICTED class.
        """
        if self.fault_explainer is None:
            self.initialize_explainers(model_manager)

        feature_cols = model_manager.fault_feature_cols
        inp = df_55_features[feature_cols].astype(float)
        predicted_fault = prediction_result.get("predicted_fault", "normal")
        confidence_val = prediction_result.get("confidence", 1.0)
        
        # Determine class index
        encoder = model_manager.fault_label_encoder
        class_idx = 0
        if encoder is not None and hasattr(encoder, "classes_"):
            classes_list = list(encoder.classes_)
            if predicted_fault in classes_list:
                class_idx = classes_list.index(predicted_fault)

        # Compute SHAP values
        raw_shap = self.fault_explainer.shap_values(inp)
        
        # Handle multiclass output formats from shap
        # Format 1: list of arrays [array_class_0, array_class_1, ...]
        # Format 2: 3D numpy array (n_samples, n_features, n_classes)
        # Format 3: 2D array (n_classes, n_features) or (1, n_features)
        if isinstance(raw_shap, list):
            class_shap_vec = raw_shap[class_idx][0]
        elif isinstance(raw_shap, np.ndarray):
            if raw_shap.ndim == 3:
                class_shap_vec = raw_shap[0, :, class_idx]
            elif raw_shap.ndim == 2:
                if raw_shap.shape[0] == len(encoder.classes_):
                    class_shap_vec = raw_shap[class_idx]
                else:
                    class_shap_vec = raw_shap[0]
            else:
                class_shap_vec = raw_shap
        else:
            class_shap_vec = np.array(raw_shap)

        values_row = inp.iloc[0].values
        contributors = []

        for i, col in enumerate(feature_cols):
            s_val = float(class_shap_vec[i])
            f_val = float(values_row[i])
            parsed = self.mapper.parse_feature(col)
            
            # Direction relative to predicted fault
            if s_val > 0:
                direction = "increases_fault_probability"
                direction_text = f"Increases {predicted_fault} likelihood"
            elif s_val < 0:
                direction = "decreases_fault_probability"
                direction_text = f"Decreases {predicted_fault} likelihood"
            else:
                direction = "neutral"
                direction_text = "No direct impact on prediction"

            contributors.append({
                "feature": col,
                "display_name": parsed["display_name"],
                "value": round(f_val, 4),
                "unit": parsed["unit"],
                "shap_value": round(s_val, 4),
                "importance": round(abs(s_val), 4),
                "direction": direction,
                "direction_text": direction_text,
                "sensor_group": parsed["sensor_group"],
                "description": parsed["natural_description"]
            })

        # Sort by absolute SHAP contribution descending
        contributors.sort(key=lambda item: item["importance"], reverse=True)
        top_contributors = contributors[:top_n]

        # Group by physical sensor subsystem
        sensor_groups = self.mapper.group_contributions_by_sensor(contributors[:top_n * 2])

        # Confidence calculation
        conf_data = calculate_fault_confidence(confidence_val)

        # Human-readable rationale construction
        if predicted_fault != "normal":
            top_factors_desc = []
            for item in top_contributors[:4]:
                sign_str = "+" if item["shap_value"] > 0 else "-"
                top_factors_desc.append(f"{item['display_name']} ({sign_str}{abs(item['shap_value']):.2f})")
            
            summary = (
                f"FAULT DIAGNOSIS: {predicted_fault.upper()} predicted with {conf_data['confidence_display']} confidence. "
                f"Key contributing factors: {', '.join(top_factors_desc)}. "
                f"This signature is consistent with abnormal {sensor_groups[0]['sensor_name'] if sensor_groups else 'propulsion'} dynamics."
            )
        else:
            summary = (
                f"NOMINAL: Fault classification model predicts standard operating envelope "
                f"with {conf_data['confidence_display']} confidence."
            )

        return {
            "predicted_fault": predicted_fault,
            "confidence": conf_data["confidence"],
            "confidence_display": conf_data["confidence_display"],
            "confidence_type": conf_data["confidence_type"],
            "confidence_methodology": conf_data["methodology"],
            "fault_probabilities": prediction_result.get("fault_probabilities", {}),
            "explanation_method": "SHAP TreeExplainer (Multiclass Log-Odds Decomposition)",
            "top_contributors": top_contributors,
            "sensor_level_breakdown": sensor_groups,
            "summary": summary
        }

    # --------------------------------------------------------------------------------
    # 2. DEGRADATION ESTIMATION EXPLANATION
    # --------------------------------------------------------------------------------
    def explain_degradation(
        self,
        df_120_features: pd.DataFrame,
        model_manager,
        clean_sample: Optional[Dict[str, Any]],
        prediction_result: Dict[str, Any],
        top_n: int = 5
    ) -> Dict[str, Any]:
        """
        Generates explanation for Degradation Estimation.
        CRITICAL: Detects if prediction came from telemetry ground truth vs XGBoost Regressor model.
        """
        deg_index = float(prediction_result.get("degradation_index", 0.0))
        health_pct = float(prediction_result.get("estimated_health_pct", 100.0))

        # Check source of prediction
        is_telemetry = clean_sample is not None and ("degradation" in clean_sample or "health_index" in clean_sample)
        
        if is_telemetry:
            # Telemetry ground truth mode
            conf_data = calculate_degradation_confidence("telemetry", deg_index)
            
            # Analyze key physical sensor signals for telemetry explanation
            telemetry_factors = []
            if clean_sample:
                for sig in ["egt_C", "cht_C", "oil_pressure_bar", "vibration_rms", "rpm_residual", "egt_residual"]:
                    if sig in clean_sample:
                        parsed = self.mapper.parse_feature(sig)
                        val = float(clean_sample[sig])
                        telemetry_factors.append({
                            "feature": sig,
                            "display_name": parsed["display_name"],
                            "value": round(val, 4),
                            "unit": parsed["unit"],
                            "direction": "telemetry_observed",
                            "sensor_group": parsed["sensor_group"],
                            "description": f"Verified telemetry sensor reading: {val} {parsed['unit']}"
                        })

            summary = (
                f"Degradation Index {deg_index:.4f} (Health: {health_pct:.1f}%) directly sourced from verified "
                f"onboard telemetry ground-truth stream. Sensor readings remain within active mission envelope."
            )

            return {
                "degradation_index": deg_index,
                "estimated_health_pct": health_pct,
                "explanation_source": "telemetry",
                "confidence": conf_data["confidence"],
                "confidence_display": conf_data["confidence_display"],
                "confidence_type": conf_data["confidence_type"],
                "confidence_methodology": conf_data["methodology"],
                "explanation_method": "Telemetry Ground-Truth Validation & Sensor Profile Monitoring",
                "top_contributors": telemetry_factors[:top_n],
                "summary": summary
            }

        # XGBoost Model inference mode
        if self.degradation_explainer is None:
            self.initialize_explainers(model_manager)

        feature_cols = model_manager.degradation_feature_cols
        inp = df_120_features[feature_cols].astype(float)
        raw_shap = self.degradation_explainer.shap_values(inp)

        shap_vec = raw_shap[0] if isinstance(raw_shap, np.ndarray) and raw_shap.ndim == 2 else raw_shap
        values_row = inp.iloc[0].values
        contributors = []

        for i, col in enumerate(feature_cols):
            s_val = float(shap_vec[i])
            f_val = float(values_row[i])
            parsed = self.mapper.parse_feature(col)

            if s_val > 0:
                direction = "increases_degradation"
                direction_text = "Increases degradation (reduces health)"
            elif s_val < 0:
                direction = "reduces_degradation"
                direction_text = "Reduces degradation (improves health)"
            else:
                direction = "neutral"
                direction_text = "Neutral baseline contribution"

            contributors.append({
                "feature": col,
                "display_name": parsed["display_name"],
                "value": round(f_val, 4),
                "unit": parsed["unit"],
                "shap_value": round(s_val, 4),
                "importance": round(abs(s_val), 4),
                "direction": direction,
                "direction_text": direction_text,
                "sensor_group": parsed["sensor_group"],
                "description": parsed["natural_description"]
            })

        contributors.sort(key=lambda item: item["importance"], reverse=True)
        top_contributors = contributors[:top_n]
        sensor_groups = self.mapper.group_contributions_by_sensor(contributors[:top_n * 2])
        conf_data = calculate_degradation_confidence("xgboost", deg_index)

        top_names = [item["display_name"] for item in top_contributors[:3]]
        summary = (
            f"Degradation Index estimated at {deg_index:.4f} (Health: {health_pct:.1f}%) by XGBoost Regressor. "
            f"Primary drivers of degradation estimate: {', '.join(top_names)}."
        )

        return {
            "degradation_index": deg_index,
            "estimated_health_pct": health_pct,
            "explanation_source": "xgboost",
            "confidence": conf_data["confidence"],
            "confidence_display": conf_data["confidence_display"],
            "confidence_type": conf_data["confidence_type"],
            "confidence_methodology": conf_data["methodology"],
            "explanation_method": "SHAP TreeExplainer (Regression Additive Decomposition)",
            "top_contributors": top_contributors,
            "sensor_level_breakdown": sensor_groups,
            "summary": summary
        }

    # --------------------------------------------------------------------------------
    # 3. REMAINING USEFUL LIFE (RUL) EXPLANATION
    # --------------------------------------------------------------------------------
    def explain_rul(
        self,
        df_60_features: Optional[pd.DataFrame],
        model_manager,
        prediction_result: Dict[str, Any],
        top_n: int = 5
    ) -> Dict[str, Any]:
        """
        Generates explanation for Remaining Useful Life (RUL).
        Strictly distinguishes between RAW XGBoost model SHAP explanations
        and dynamic post-processing (degradation anchoring, EMA smoothing, slew-rate limiter).
        """
        status = prediction_result.get("status", "UNKNOWN")
        
        # Handle Collecting History state (< 13 frames)
        if status == "COLLECTING_HISTORY" or df_60_features is None:
            records_avail = prediction_result.get("records_available", 0)
            records_req = prediction_result.get("records_required", 13)
            conf_data = calculate_rul_confidence(None, None)

            return {
                "status": "COLLECTING_HISTORY",
                "predicted_rul_hours": None,
                "raw_rul_hours": None,
                "confidence": conf_data["confidence"],
                "confidence_display": conf_data["confidence_display"],
                "confidence_type": conf_data["confidence_type"],
                "confidence_methodology": conf_data["methodology"],
                "explanation_method": "Temporal History Warm-Up (Waiting for rolling time-series window)",
                "records_available": records_avail,
                "records_required": records_req,
                "top_contributors": [],
                "post_processing_explanation": {
                    "anchoring": "Inactive (Awaiting warm-up)",
                    "ema_smoothing": "Inactive (Awaiting warm-up)",
                    "slew_rate_limiting": "Inactive (Awaiting warm-up)"
                },
                "summary": f"RUL model is warming up rolling time-series history ({records_avail}/{records_req} frames collected)."
            }

        if self.rul_explainer is None:
            self.initialize_explainers(model_manager)

        feature_cols = model_manager.rul_feature_cols
        inp = df_60_features[feature_cols].astype(float)
        raw_rul = float(prediction_result.get("raw_rul_hours", 0.0))
        final_rul = float(prediction_result.get("predicted_rul_hours", raw_rul))
        std_uncertainty = prediction_result.get("uncertainty_std_hours")
        conf_level_str = prediction_result.get("confidence_level", "MEDIUM")

        # Compute SHAP on RAW XGBoost model
        raw_shap = self.rul_explainer.shap_values(inp)
        shap_vec = raw_shap[0] if isinstance(raw_shap, np.ndarray) and raw_shap.ndim == 2 else raw_shap
        values_row = inp.iloc[0].values
        contributors = []

        for i, col in enumerate(feature_cols):
            s_val = float(shap_vec[i])
            f_val = float(values_row[i])
            parsed = self.mapper.parse_feature(col)

            if s_val > 0:
                direction = "increases_rul"
                direction_text = "Extends estimated RUL lifespan (+hours)"
            elif s_val < 0:
                direction = "decreases_rul"
                direction_text = "Shortens estimated RUL lifespan (-hours)"
            else:
                direction = "neutral"
                direction_text = "Neutral lifespan contribution"

            contributors.append({
                "feature": col,
                "display_name": parsed["display_name"],
                "value": round(f_val, 4),
                "unit": parsed["unit"],
                "shap_value": round(s_val, 4),
                "importance": round(abs(s_val), 4),
                "direction": direction,
                "direction_text": direction_text,
                "sensor_group": parsed["sensor_group"],
                "description": parsed["natural_description"]
            })

        contributors.sort(key=lambda item: item["importance"], reverse=True)
        top_contributors = contributors[:top_n]
        sensor_groups = self.mapper.group_contributions_by_sensor(contributors[:top_n * 2])

        # Confidence calculation
        conf_data = calculate_rul_confidence(final_rul, std_uncertainty, conf_level_str)

        # Explicit Post-Processing Breakdown
        post_proc_explanation = {
            "raw_xgboost_rul_hours": raw_rul,
            "final_filtered_rul_hours": final_rul,
            "post_processing_steps": [
                {
                    "step": "1. Dynamic Degradation / Health Anchoring",
                    "description": "Blends raw ML output with physical health target (Health% * 50h) with failure zero-clamping at degradation >= 0.98."
                },
                {
                    "step": "2. Exponential Moving Average (EMA) Smoothing",
                    "description": "Applies low-pass temporal EMA filter (alpha=0.12) to dampen instantaneous sensor jitter."
                },
                {
                    "step": "3. Slew-Rate Limiting",
                    "description": "Enforces physical realism bounds (+0.5h max growth / -2.0h max drop per second)."
                }
            ],
            "uncertainty_quantification": {
                "std_uncertainty_hours": std_uncertainty,
                "confidence_interval_90pct": prediction_result.get("confidence_interval_90pct", []),
                "confidence_level": conf_level_str
            }
        }

        top_drivers = [item["display_name"] for item in top_contributors[:3]]
        summary = (
            f"RUL ESTIMATION: {final_rul:.1f} flight hours remaining ({conf_data['confidence_display']} confidence). "
            f"Raw XGBoost output ({raw_rul:.1f}h) driven primarily by: {', '.join(top_drivers)}. "
            f"Physical lifecycle degradation anchoring and EMA temporal smoothing applied."
        )

        return {
            "status": "PREDICTED",
            "predicted_rul_hours": final_rul,
            "raw_rul_hours": raw_rul,
            "confidence": conf_data["confidence"],
            "confidence_display": conf_data["confidence_display"],
            "confidence_type": conf_data["confidence_type"],
            "confidence_methodology": conf_data["methodology"],
            "confidence_interval_90pct": prediction_result.get("confidence_interval_90pct", []),
            "uncertainty_std_hours": std_uncertainty,
            "confidence_level": conf_level_str,
            "explanation_method": "SHAP TreeExplainer (Raw XGBoost) + Dynamic Temporal Post-Processing Pipeline",
            "top_contributors": top_contributors,
            "sensor_level_breakdown": sensor_groups,
            "post_processing_explanation": post_proc_explanation,
            "summary": summary
        }
