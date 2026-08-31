import os
import sys
import logging
import json
import pandas as pd
import numpy as np

# Ensure workspace root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.model_loader import DigitalTwinModelManager
from backend.feature_engine import DigitalTwinFeatureEngine
from explainability.xai_engine import DigitalTwinXAIEngine
from explainability.feature_mapper import FeatureMapper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("TestXAI")

def test_xai_pipeline():
    logger.info("==================================================================")
    logger.info("STARTING XAI (EXPLAINABLE AI) COMPREHENSIVE VERIFICATION SUITE")
    logger.info("==================================================================")

    # 1. Initialize Model Manager & Feature Engine
    model_manager = DigitalTwinModelManager()
    model_manager.load_all_models()
    assert model_manager._is_loaded, "Model Manager failed to load frozen models!"
    logger.info("FROZEN MODELS LOADED SUCCESSFULLY (No retraining, no weight changes).")

    feature_engine = DigitalTwinFeatureEngine()
    xai_engine = DigitalTwinXAIEngine()
    xai_engine.initialize(model_manager)
    logger.info("XAI Engine and SHAP TreeExplainers initialized.")

    # 2. Test Feature Mapper
    mapper = FeatureMapper()
    parsed_egt = mapper.parse_feature("egt_C_slope_6")
    assert parsed_egt["base_sensor"] == "egt_C"
    assert parsed_egt["operation"] == "slope"
    assert parsed_egt["window_or_lag"] == 6
    logger.info(f"Feature Mapper Test 1: 'egt_C_slope_6' -> {parsed_egt['display_name']} ({parsed_egt['sensor_group']})")

    parsed_cht_mean = mapper.parse_feature("cht_C_rollmean15")
    assert parsed_cht_mean["base_sensor"] == "cht_C"
    assert parsed_cht_mean["operation"] == "rolling_mean"
    assert parsed_cht_mean["window_or_lag"] == 15
    logger.info(f"Feature Mapper Test 2: 'cht_C_rollmean15' -> {parsed_cht_mean['display_name']}")

    parsed_vib_diff = mapper.parse_feature("vibration_rms_diff10")
    assert parsed_vib_diff["base_sensor"] == "vibration_rms"
    assert parsed_vib_diff["operation"] == "diff"
    assert parsed_vib_diff["window_or_lag"] == 10
    logger.info(f"Feature Mapper Test 3: 'vibration_rms_diff10' -> {parsed_vib_diff['display_name']}")

    # 3. Test Warm-Up Scenario (< 13 frames for RUL)
    logger.info("------------------------------------------------------------------")
    logger.info("TEST CASE 1: Warm-Up Telemetry Frame (History < 13 records)")
    logger.info("------------------------------------------------------------------")
    raw_nominal = {
        "rpm": 2300.0,
        "cht_C": 135.0,
        "egt_C": 670.0,
        "oil_temperature_C": 85.0,
        "oil_pressure_bar": 4.5,
        "vibration_rms": 0.15,
        "fuel_flow_kg_s": 0.005,
        "air_mass_flow_kg_s": 0.08,
        "power_W": 36000.0,
        "torque_Nm": 150.0,
        "battery_voltage_V": 28.0,
        "alternator_current_A": 25.0,
        "alternator_health": 1.0,
        "injection_timing_deg": 15.0
    }
    fv_warmup = feature_engine.generate_all_feature_vectors(raw_nominal, model_manager)
    preds_warmup = model_manager.predict_all(fv_warmup, buffer_len=len(feature_engine.buffer))
    xai_warmup = xai_engine.explain(fv_warmup, preds_warmup, model_manager)

    assert xai_warmup["rul"]["status"] == "COLLECTING_HISTORY"
    assert xai_warmup["rul"]["predicted_rul_hours"] is None
    assert xai_warmup["rul"]["confidence_type"] == "collecting_history"
    logger.info(f"Warm-Up Status: {xai_warmup['overall_status']} | RUL Status: {xai_warmup['rul']['status']}")
    logger.info(f"Anomaly Confidence: {xai_warmup['anomaly']['confidence_display']} (Type: {xai_warmup['anomaly']['confidence_type']})")

    # 4. Fill History Buffer for RUL (15 frames)
    logger.info("Filling history buffer to 15 frames for RUL testing...")
    for _ in range(14):
        fv_nominal = feature_engine.generate_all_feature_vectors(raw_nominal, model_manager)
    
    preds_nominal = model_manager.predict_all(fv_nominal, buffer_len=len(feature_engine.buffer))
    xai_nominal = xai_engine.explain(fv_nominal, preds_nominal, model_manager)

    assert xai_nominal["rul"]["status"] == "PREDICTED"
    assert xai_nominal["rul"]["predicted_rul_hours"] is not None
    assert xai_nominal["rul"]["confidence_type"] == "uncertainty_based"
    assert "post_processing_explanation" in xai_nominal["rul"]
    logger.info(f"Nominal Engine -> Predicted RUL: {xai_nominal['rul']['predicted_rul_hours']}h (Confidence: {xai_nominal['rul']['confidence_display']})")
    logger.info(f"Nominal Status: {xai_nominal['overall_status']}")
    logger.info(f"Human Summary Preview:\n{xai_nominal['human_summary']}")

    # 5. Test Anomaly & Fault Scenario (Synthetic Overheating)
    logger.info("------------------------------------------------------------------")
    logger.info("TEST CASE 2: Synthetic Overheating Fault Injection")
    logger.info("------------------------------------------------------------------")
    raw_overheating = dict(raw_nominal)
    raw_overheating["cht_C"] = 195.0
    raw_overheating["egt_C"] = 780.0
    raw_overheating["vibration_rms"] = 0.45
    raw_overheating["expected_cht_C"] = 135.0
    raw_overheating["expected_egt_C"] = 670.0

    # Push multiple abnormal frames to simulate realistic dynamic trend
    for _ in range(5):
        fv_overheating = feature_engine.generate_all_feature_vectors(raw_overheating, model_manager)

    preds_overheating = model_manager.predict_all(fv_overheating, buffer_len=len(feature_engine.buffer))
    xai_overheating = xai_engine.explain(fv_overheating, preds_overheating, model_manager)

    logger.info(f"Fault Predicted: {preds_overheating['fault_classification']['predicted_fault']} (Confidence: {xai_overheating['fault']['confidence_display']})")
    logger.info(f"Anomaly Detected: {xai_overheating['anomaly']['is_anomaly']} (Score: {xai_overheating['anomaly']['anomaly_score']}, Confidence: {xai_overheating['anomaly']['confidence_display']})")
    logger.info("Top Fault Contributors (SHAP):")
    for item in xai_overheating["fault"]["top_contributors"][:4]:
        logger.info(f"  - {item['display_name']} ({item['feature']}): SHAP={item['shap_value']}, Value={item['value']} {item['unit']} ({item['direction_text']})")

    logger.info("Sensor-Level Aggregated Breakdown:")
    for sg in xai_overheating["fault"]["sensor_level_breakdown"][:3]:
        logger.info(f"  - Sensor: {sg['sensor_name']} | Level: {sg['contribution_level']} (Importance: {sg['total_importance']})")

    assert len(xai_overheating["fault"]["top_contributors"]) > 0
    assert xai_overheating["fault"]["confidence_type"] == "model_probability"

    # 6. Test Degradation Explanation (Telemetry Ground-Truth vs XGBoost Model)
    logger.info("------------------------------------------------------------------")
    logger.info("TEST CASE 3: Degradation Source Verification (Telemetry vs Model)")
    logger.info("------------------------------------------------------------------")
    
    # Case A: Telemetry ground truth present
    raw_with_deg = dict(raw_nominal)
    raw_with_deg["degradation"] = 0.42
    fv_deg_telem = feature_engine.generate_all_feature_vectors(raw_with_deg, model_manager)
    preds_deg_telem = model_manager.predict_all(fv_deg_telem, buffer_len=len(feature_engine.buffer))
    xai_deg_telem = xai_engine.explain(fv_deg_telem, preds_deg_telem, model_manager)
    
    assert xai_deg_telem["degradation"]["explanation_source"] == "telemetry"
    assert xai_deg_telem["degradation"]["confidence_type"] == "telemetry_based"
    logger.info(f"Telemetry-Sourced Degradation: {xai_deg_telem['degradation']['degradation_index']} (Source: {xai_deg_telem['degradation']['explanation_source']}, Conf: {xai_deg_telem['degradation']['confidence_display']})")

    # Case B: Pure Model inference (no telemetry ground truth)
    raw_no_deg = dict(raw_nominal)
    raw_no_deg.pop("degradation", None)
    raw_no_deg.pop("health_index", None)
    # create clean sample copy without degradation keys
    fv_deg_model = feature_engine.generate_all_feature_vectors(raw_no_deg, model_manager)
    fv_deg_model["clean_sample"].pop("degradation", None)
    fv_deg_model["clean_sample"].pop("health_index", None)
    
    preds_deg_model = model_manager.predict_all(fv_deg_model, buffer_len=len(feature_engine.buffer))
    xai_deg_model = xai_engine.explain(fv_deg_model, preds_deg_model, model_manager)
    
    assert xai_deg_model["degradation"]["explanation_source"] == "xgboost"
    assert len(xai_deg_model["degradation"]["top_contributors"]) > 0
    logger.info(f"XGBoost-Sourced Degradation: {xai_deg_model['degradation']['degradation_index']} (Source: {xai_deg_model['degradation']['explanation_source']}, Top Driver: {xai_deg_model['degradation']['top_contributors'][0]['display_name']})")

    # 7. JSON Serialization Verification
    json_str = json.dumps(xai_overheating, indent=2)
    assert len(json_str) > 100, "JSON serialization failed!"
    logger.info("JSON Serialization test passed without numpy errors.")

    logger.info("==================================================================")
    logger.info("ALL XAI TESTS PASSED CLEANLY AND FULLY VERIFIED!")
    logger.info("==================================================================")

if __name__ == "__main__":
    test_xai_pipeline()
