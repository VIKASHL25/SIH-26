import logging
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

from explainability.feature_mapper import FeatureMapper
from explainability.anomaly_explainer import AnomalyExplainer
from explainability.shap_explainer import DigitalTwinTreeExplainer

logger = logging.getLogger("DigitalTwinXAIEngine")

def _sanitize_for_json(obj: Any) -> Any:
    """Recursively converts numpy scalars and arrays to native Python types for clean JSON serialization."""
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return [_sanitize_for_json(x) for x in obj.tolist()]
    elif isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(x) for x in obj]
    return obj

class DigitalTwinXAIEngine:
    """
    Central Explainable AI (XAI) Engine for Aero Piston Engine Digital Twin.
    
    Coordinates:
    1. Feature mapping & engineering-to-sensor translation.
    2. Sensitivity & standardized deviation analysis for Isolation Forest Anomaly Detection.
    3. Multiclass SHAP TreeExplainer for Fault Classification.
    4. Regression SHAP TreeExplainer for Degradation Estimation (with telemetry-vs-XGBoost source detection).
    5. Regression SHAP TreeExplainer for RUL with explicit Raw-vs-Post-Processing breakdown.
    6. Synthesized unified engineering narrative & maintenance advisories.
    """

    def __init__(self, feature_mapper: Optional[FeatureMapper] = None):
        self.mapper = feature_mapper or FeatureMapper()
        self.anomaly_explainer = AnomalyExplainer(feature_mapper=self.mapper)
        self.tree_explainer = DigitalTwinTreeExplainer(feature_mapper=self.mapper)
        self._initialized = False

    def initialize(self, model_manager):
        """Initializes and caches model explainers."""
        if not self._initialized:
            self.tree_explainer.initialize_explainers(model_manager)
            self._initialized = True
            logger.info("DigitalTwinXAIEngine initialized and explainers cached.")

    def explain(
        self,
        feature_vectors: Dict[str, Any],
        predictions: Dict[str, Any],
        model_manager,
        top_n: int = 5
    ) -> Dict[str, Any]:
        """
        Main entry point for generating full-system explainability reports.
        
        Args:
            feature_vectors: Dictionary containing "anomaly", "degradation", "fault", "rul", and "clean_sample"
            predictions: Prediction outputs from model_manager.predict_all()
            model_manager: DigitalTwinModelManager instance with frozen models
            top_n: Number of top contributors to return per model (default: 5)
            
        Returns:
            Structured, JSON-serializable dictionary with comprehensive explanations across all 4 models.
        """
        if not self._initialized:
            self.initialize(model_manager)

        clean_sample = feature_vectors.get("clean_sample", {})

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

        anomaly_df = _to_df(feature_vectors.get("anomaly"))
        degradation_df = _to_df(feature_vectors.get("degradation"))
        fault_df = _to_df(feature_vectors.get("fault"))
        rul_df = _to_df(feature_vectors.get("rul"))

        # 1. Anomaly Model Explanation
        anomaly_res = predictions.get("anomaly_detection", {})
        anomaly_explanation = self.anomaly_explainer.explain(
            df_13_features=anomaly_df,
            anomaly_model=model_manager.anomaly_model,
            anomaly_scaler=model_manager.anomaly_scaler,
            feature_cols=model_manager.anomaly_feature_cols,
            prediction_result=anomaly_res,
            top_n=top_n
        )

        # 2. Fault Model Explanation
        fault_res = predictions.get("fault_classification", {})
        fault_explanation = self.tree_explainer.explain_fault(
            df_55_features=fault_df,
            model_manager=model_manager,
            prediction_result=fault_res,
            top_n=top_n
        )

        # 3. Degradation Model Explanation
        deg_res = predictions.get("degradation_estimation", {})
        degradation_explanation = self.tree_explainer.explain_degradation(
            df_120_features=degradation_df,
            model_manager=model_manager,
            clean_sample=clean_sample,
            prediction_result=deg_res,
            top_n=top_n
        )

        # 4. RUL Model Explanation
        rul_res = predictions.get("rul_prediction", {})
        rul_explanation = self.tree_explainer.explain_rul(
            df_60_features=rul_df,
            model_manager=model_manager,
            prediction_result=rul_res,
            top_n=top_n
        )

        # 5. Synthesize Unified Engineering Interpretation & Recommendations
        overall_status = predictions.get("status", "NOMINAL")
        engineering_summary = self._generate_engineering_summary(
            overall_status=overall_status,
            anomaly_exp=anomaly_explanation,
            fault_exp=fault_explanation,
            deg_exp=degradation_explanation,
            rul_exp=rul_explanation,
            clean_sample=clean_sample
        )

        recommendations = self._generate_maintenance_recommendations(
            overall_status=overall_status,
            anomaly_exp=anomaly_explanation,
            fault_exp=fault_explanation,
            deg_exp=degradation_explanation,
            rul_exp=rul_explanation,
            clean_sample=clean_sample
        )

        result = {
            "overall_status": overall_status,
            "anomaly": anomaly_explanation,
            "fault": fault_explanation,
            "degradation": degradation_explanation,
            "rul": rul_explanation,
            "engineering_interpretation": engineering_summary["interpretation"],
            "human_summary": engineering_summary["human_summary"],
            "recommendations": recommendations
        }

        return _sanitize_for_json(result)

    def _generate_engineering_summary(
        self,
        overall_status: str,
        anomaly_exp: Dict[str, Any],
        fault_exp: Dict[str, Any],
        deg_exp: Dict[str, Any],
        rul_exp: Dict[str, Any],
        clean_sample: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Synthesizes parameter-aware engineering rationale and explainable AI narrative."""
        predicted_fault = fault_exp.get("predicted_fault", "normal")
        is_anomaly = anomaly_exp.get("is_anomaly", False)
        health_pct = deg_exp.get("estimated_health_pct", 100.0)
        rul_hours = rul_exp.get("predicted_rul_hours")
        sample = clean_sample or {}

        rpm = sample.get("rpm", 2300.0)
        cht = sample.get("cht_C", 135.0)
        egt = sample.get("egt_C", 670.0)
        oil_p = sample.get("oil_pressure_bar", 4.5)
        oil_t = sample.get("oil_temperature_C", 85.0)
        vib = sample.get("vibration_rms", 0.15)
        cht_res = sample.get("cht_residual", 0.0)
        egt_res = sample.get("egt_residual", 0.0)

        lines = []
        if predicted_fault != "normal":
            lines.append(f"ENGINE STATUS: FAULT DETECTED ({predicted_fault.upper()})")
            lines.append(f"Model Confidence: {fault_exp.get('confidence_display', 'N/A')}")
            lines.append("\nWhy the model predicts this:")
            for i, item in enumerate(fault_exp.get("top_contributors", [])[:4], 1):
                sign_str = "+" if item.get("shap_value", 0.0) > 0 else "-"
                lines.append(f"{i}. {item['display_name']} ({item['direction_text']} | SHAP {sign_str}{abs(item.get('shap_value', 0.0)):.3f})")
            
            lines.append("\nEngineering Assessment:")
            if predicted_fault == "overheating":
                interpretation = (
                    f"Thermal distress detected (CHT: {cht:.1f}°C, EGT: {egt:.1f}°C). "
                    f"Thermodynamic CHT residual is {cht_res:+.1f}°C and EGT residual is {egt_res:+.1f}°C relative to physics expectation. "
                    f"SHAP attribution identifies elevated thermal slope and rolling temperature as dominant drivers."
                )
            elif predicted_fault == "lubrication_degradation":
                interpretation = (
                    f"Lubrication system compromise detected (Oil Pressure: {oil_p:.2f} bar, Oil Temp: {oil_t:.1f}°C, Vibration: {vib:.3f}g). "
                    f"Oil pressure is significantly below normal baseline (4.5 bar). "
                    f"SHAP attribution identifies reduced oil pressure and hydraulic variance as key failure signatures."
                )
            elif predicted_fault == "injector_degradation":
                interpretation = (
                    f"Fuel injection irregularity detected (Fuel Flow: {sample.get('fuel_flow_kg_s', 0.0):.4f} kg/s, EGT: {egt:.1f}°C). "
                    f"Fuel-air ratio imbalance and combustion physics residual indicate uneven fuel atomization."
                )
            elif predicted_fault == "misfire":
                interpretation = (
                    f"Combustion misfire detected (Vibration: {vib:.3f}g, RPM Residual: {sample.get('rpm_residual', 0.0):+.1f} RPM). "
                    f"Torque oscillation and intermittent cylinder deceleration observed."
                )
            elif predicted_fault == "sensor_fault":
                interpretation = (
                    f"Sensor telemetry inconsistency detected. Monitored sensor signals diverge from thermodynamic cross-channel correlation."
                )
            else:
                top_sensor_name = fault_exp.get('sensor_level_breakdown', [{}])[0].get('sensor_name', 'subsystem')
                interpretation = f"Model identifies signature consistent with {predicted_fault}, driven primarily by {top_sensor_name} parameter deviation."

            lines.append(interpretation)

        elif is_anomaly:
            lines.append("ENGINE STATUS: ANOMALOUS OPERATING ENVELOPE")
            lines.append(f"Anomaly Confidence Indicator: {anomaly_exp.get('confidence_display', 'N/A')}")
            lines.append("\nKey abnormal indicators:")
            for i, g in enumerate(anomaly_exp.get("sensor_level_breakdown", [])[:3], 1):
                lines.append(f"{i}. {g['sensor_name']} (Total Sensitivity: {g['total_importance']:.3f})")
            lines.append("\nEngineering Assessment:")
            interpretation = (
                f"Multivariate telemetry anomaly (Score: {anomaly_exp.get('anomaly_score', 0.0):+.4f}). "
                f"Sensors exhibit deviation from calibrated nominal flight envelope (CHT: {cht:.1f}°C, EGT: {egt:.1f}°C, Oil Press: {oil_p:.2f} bar, Vib: {vib:.3f}g)."
            )
            lines.append(interpretation)
        else:
            lines.append("ENGINE STATUS: NOMINAL")
            lines.append("All 4 AI models indicate standard operating envelope within physical flight bounds.")
            interpretation = (
                f"Nominal powertrain equilibrium maintained (RPM: {rpm:.0f}, CHT: {cht:.1f}°C, EGT: {egt:.1f}°C, Oil Press: {oil_p:.2f} bar, Vib: {vib:.3f}g). "
                f"Thermodynamic residuals (CHT Δ: {cht_res:+.1f}°C) and mechanical parameters reside within calibrated nominal bounds."
            )

        # Degradation & RUL line
        lines.append(f"\nHealth Index: {health_pct:.1f}% | Degradation Source: {deg_exp.get('explanation_source', 'N/A')}")
        if rul_hours is not None:
            lines.append(f"Estimated RUL: {rul_hours:.1f} hours ({rul_exp.get('confidence_display', 'N/A')} confidence)")
        else:
            lines.append("Estimated RUL: Initializing history window...")

        human_summary = "\n".join(lines)

        return {
            "human_summary": human_summary,
            "interpretation": interpretation
        }

    def _generate_maintenance_recommendations(
        self,
        overall_status: str,
        anomaly_exp: Dict[str, Any],
        fault_exp: Dict[str, Any],
        deg_exp: Dict[str, Any],
        rul_exp: Dict[str, Any],
        clean_sample: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Generates actionable propulsion engineering and flight operations recommendations."""
        recs = []
        fault = fault_exp.get("predicted_fault", "normal")
        is_anomaly = anomaly_exp.get("is_anomaly", False)
        health_pct = deg_exp.get("estimated_health_pct", 100.0)
        rul_hours = rul_exp.get("predicted_rul_hours")
        sample = clean_sample or {}

        if fault == "overheating":
            cht_val = sample.get("cht_C", 180.0)
            recs.append(f"Thermal management: Reduce engine power/throttle and enrich fuel mixture to cool cylinder heads (current CHT: {cht_val:.1f}°C).")
            recs.append("Ground inspection: Inspect cylinder cooling cowl baffles, air duct intake, and EGT thermocouple probe calibration.")
        elif fault == "lubrication_degradation":
            oil_p = sample.get("oil_pressure_bar", 1.5)
            recs.append(f"Hydraulic alert: Oil pressure critically low ({oil_p:.2f} bar vs nominal 4.5 bar). Avoid high-G maneuvers and power spikes.")
            recs.append("Maintenance action: Inspect oil pump, filter screen for metal particles, and verify oil viscosity/fluid level.")
        elif fault == "injector_degradation":
            recs.append("Fuel system check: Verify fuel rail pressure and check injector pulse width telemetry for cylinder balance.")
            recs.append("Maintenance action: Schedule ultrasonic cleaning and spray pattern test of fuel injection nozzles.")
        elif fault == "misfire":
            recs.append("Ignition check: Inspect ignition harness, magneto timing, and check spark plugs for carbon fouling or electrode gap wear.")
        elif fault == "sensor_fault":
            recs.append("Telemetry check: Perform diagnostic cross-check against redundant sensor channels and execute sensor recalibration routine.")
        elif is_anomaly:
            recs.append("Flight monitoring: Cross-reference engine vibration and physics thermal residuals against active flight phase profile.")

        if health_pct < 50.0:
            recs.append(f"Wear advisory: Engine Health Index ({health_pct:.1f}%) is in critical wear zone. Schedule depot overhaul.")
        
        if rul_hours is not None and rul_hours < 25.0:
            recs.append(f"RUL alert: Remaining Useful Life is low ({rul_hours:.1f} flight hours remaining). Plan scheduled engine replacement.")

        if not recs:
            recs.append("Continue standard mission flight profile. All engine subsystems operating within normal parameters. Routine scheduled preventive maintenance applies.")

        return recs
