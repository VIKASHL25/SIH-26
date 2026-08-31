import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from explainability.feature_mapper import FeatureMapper
from explainability.confidence import calculate_anomaly_confidence

class AnomalyExplainer:
    """
    Explainability Engine for Isolation Forest Anomaly Detection Model.
    
    Instead of forcing TreeSHAP onto Isolation Forest, this explainer uses
    rigorous Multi-Factor Sensitivity & Standardized Deviation Analysis:
    1. Feature-wise nominal counterfactual perturbation:
       Evaluates decision_function recovery when replacing feature i with its calibrated nominal mean.
       delta_score_i = decision_function(X_nominal_i) - decision_function(X)
    2. Scaler Z-score deviation from empirical training distribution:
       z_i = (x_i - mean_i) / scale_i
    3. Translates engineered & physics features into sensor-level root causes.
    """

    def __init__(self, feature_mapper: Optional[FeatureMapper] = None):
        self.mapper = feature_mapper or FeatureMapper()

    def explain(
        self,
        df_13_features: pd.DataFrame,
        anomaly_model,
        anomaly_scaler,
        feature_cols: List[str],
        prediction_result: Dict[str, Any],
        top_n: int = 5
    ) -> Dict[str, Any]:
        """
        Generates local explanation for the Anomaly Detection inference.
        """
        # Extract raw features
        input_data = df_13_features[feature_cols].copy()
        raw_vals = input_data.values[0]

        # Scaled feature vector
        scaled_vec = anomaly_scaler.transform(input_data)[0]
        base_decision = float(prediction_result.get("decision_function", anomaly_model.decision_function([scaled_vec])[0]))
        anomaly_score = float(prediction_result.get("anomaly_score", -base_decision))
        is_anomaly = bool(prediction_result.get("is_anomaly", anomaly_score >= 0.0))

        # 1. Feature perturbation sensitivity analysis
        # For each feature, evaluate how much decision_function improves when setting feature to scaled=0 (nominal mean)
        contributions = []
        n_features = len(feature_cols)

        # Batch evaluation for performance
        perturbed_batch = np.tile(scaled_vec, (n_features, 1))
        for i in range(n_features):
            perturbed_batch[i, i] = 0.0  # Set to scaled nominal mean (0.0 in StandardScaler space)

        perturbed_decisions = anomaly_model.decision_function(perturbed_batch)

        for i, col in enumerate(feature_cols):
            x_val = float(raw_vals[i])
            z_val = float(scaled_vec[i])
            nominal_mean = float(anomaly_scaler.mean_[i]) if hasattr(anomaly_scaler, "mean_") else 0.0
            scale_val = float(anomaly_scaler.scale_[i]) if hasattr(anomaly_scaler, "scale_") else 1.0

            # Sensitivity: how much replacing feature with nominal improves normal decision score
            recovery_delta = float(perturbed_decisions[i] - base_decision)

            # Combined importance score (weighted sensitivity + standardized z-score deviation)
            importance = max(0.0, recovery_delta * 0.7 + max(0.0, abs(z_val) - 1.0) * 0.1)
            
            # Direction relative to normal envelope
            if abs(z_val) >= 1.0 or recovery_delta > 0.01:
                if x_val > nominal_mean:
                    direction = "elevated_above_normal"
                    direction_text = f"Value is elevated (+{abs(z_val):.1f}σ above baseline)"
                else:
                    direction = "depressed_below_normal"
                    direction_text = f"Value is below normal (-{abs(z_val):.1f}σ below baseline)"
            else:
                direction = "within_nominal_envelope"
                direction_text = "Operating within nominal bounds"

            parsed = self.mapper.parse_feature(col)

            contributions.append({
                "feature": col,
                "display_name": parsed["display_name"],
                "value": round(x_val, 4),
                "unit": parsed["unit"],
                "z_score": round(z_val, 2),
                "sensitivity_score": round(recovery_delta, 4),
                "importance": round(importance, 4),
                "direction": direction,
                "direction_text": direction_text,
                "sensor_group": parsed["sensor_group"],
                "description": parsed["natural_description"]
            })

        # Sort features by importance descending
        contributions.sort(key=lambda item: (item["importance"], abs(item["z_score"])), reverse=True)
        top_contributors = contributions[:top_n]

        # Group by physical sensor subsystem
        sensor_groups = self.mapper.group_contributions_by_sensor(contributions[:top_n * 2])

        # Compute confidence indicator
        conf_data = calculate_anomaly_confidence(anomaly_score, threshold=0.0, is_anomaly=is_anomaly)

        # Human summary construction
        if is_anomaly:
            top_sensor_names = [g["sensor_name"] for g in sensor_groups[:3]]
            summary = (
                f"ANOMALY DETECTED: Operating parameters deviate from nominal baseline envelope. "
                f"Primary abnormal indicators are {', '.join(top_sensor_names)}. "
                f"These variations contribute to the abnormal operating pattern."
            )
        else:
            summary = (
                "NOMINAL OPERATION: All monitored engine telemetry parameters and physics residuals "
                "are operating within calibrated statistical envelopes."
            )

        return {
            "is_anomaly": is_anomaly,
            "anomaly_score": round(anomaly_score, 4),
            "decision_function": round(base_decision, 4),
            "confidence": conf_data["confidence"],
            "confidence_display": conf_data["confidence_display"],
            "confidence_type": conf_data["confidence_type"],
            "confidence_methodology": conf_data["methodology"],
            "explanation_method": "Isolation Forest Counterfactual Sensitivity & Z-Score Deviation Analysis",
            "top_contributors": top_contributors,
            "sensor_level_breakdown": sensor_groups,
            "summary": summary
        }
