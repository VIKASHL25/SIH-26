"""
Explainable AI (XAI) Module for Aero Piston Engine Digital Twin.

Provides local SHAP TreeExplainer and sensitivity explanations for:
1. Anomaly Detection (Isolation Forest + Scaler)
2. Degradation Estimation (XGBoost Regressor)
3. Fault Classification (Multiclass XGBoost Classifier)
4. Remaining Useful Life - RUL (XGBoost Regressor + Dynamic Temporal Post-Processing)
"""

from explainability.xai_engine import DigitalTwinXAIEngine
from explainability.feature_mapper import FeatureMapper
from explainability.anomaly_explainer import AnomalyExplainer
from explainability.shap_explainer import DigitalTwinTreeExplainer
from explainability.confidence import (
    calculate_anomaly_confidence,
    calculate_fault_confidence,
    calculate_degradation_confidence,
    calculate_rul_confidence,
)

__all__ = [
    "DigitalTwinXAIEngine",
    "FeatureMapper",
    "AnomalyExplainer",
    "DigitalTwinTreeExplainer",
    "calculate_anomaly_confidence",
    "calculate_fault_confidence",
    "calculate_degradation_confidence",
    "calculate_rul_confidence",
]
