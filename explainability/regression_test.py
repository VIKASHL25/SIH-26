import os
import sys
import logging
import pandas as pd
import numpy as np

# Ensure workspace root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.model_loader import DigitalTwinModelManager
from backend.feature_engine import DigitalTwinFeatureEngine
from explainability.xai_engine import DigitalTwinXAIEngine
from backend.config import DATASET_100K_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("RegressionTest")

def run_regression_test():
    logger.info("==================================================================")
    logger.info("STARTING STRICT REGRESSION TESTING: PREDICTIONS BEFORE VS AFTER XAI")
    logger.info("==================================================================")

    # 1. Load Dataset
    df_raw = pd.read_csv(DATASET_100K_PATH)
    mission_1 = df_raw[df_raw["mission_id"] == 1].sort_values("timestamp_s").reset_index(drop=True)
    num_test_frames = 50

    # 2. Setup Reference Pipelines
    model_manager_baseline = DigitalTwinModelManager()
    model_manager_baseline.load_all_models()

    model_manager_xai = DigitalTwinModelManager()
    model_manager_xai.load_all_models()

    feature_engine_baseline = DigitalTwinFeatureEngine()
    feature_engine_xai = DigitalTwinFeatureEngine()
    xai_engine = DigitalTwinXAIEngine()
    xai_engine.initialize(model_manager_xai)

    # 3. Iterate frames and compare predictions
    for i in range(num_test_frames):
        raw_row = mission_1.iloc[i].to_dict()

        # Generate feature vectors independently
        fv_before = feature_engine_baseline.generate_all_feature_vectors(raw_row, model_manager_baseline)
        fv_after = feature_engine_xai.generate_all_feature_vectors(raw_row, model_manager_xai)

        # Baseline inference (WITHOUT XAI)
        pred_before = model_manager_baseline.predict_all(
            fv_before,
            anomaly_threshold=0.0,
            buffer_len=len(feature_engine_baseline.buffer)
        )

        # Inference WITH XAI
        pred_after = model_manager_xai.predict_all(
            fv_after,
            anomaly_threshold=0.0,
            buffer_len=len(feature_engine_xai.buffer)
        )
        xai_out = xai_engine.explain(fv_after, pred_after, model_manager_xai)

        # -------------------------------------------------------------
        # STRICT EQUALITY CHECKS
        # -------------------------------------------------------------
        # 1. Model 1 (Anomaly Detection)
        anom_before = pred_before["anomaly_detection"]
        anom_after = pred_after["anomaly_detection"]
        assert anom_before["anomaly_score"] == anom_after["anomaly_score"], f"Anomaly score mismatch at frame {i}"
        assert anom_before["is_anomaly"] == anom_after["is_anomaly"], f"Anomaly bool mismatch at frame {i}"
        assert anom_before["decision_function"] == anom_after["decision_function"], f"Decision function mismatch at frame {i}"

        # 2. Model 2 (Degradation Estimation)
        deg_before = pred_before["degradation_estimation"]
        deg_after = pred_after["degradation_estimation"]
        assert deg_before["degradation_index"] == deg_after["degradation_index"], f"Degradation index mismatch at frame {i}"
        assert deg_before["estimated_health_pct"] == deg_after["estimated_health_pct"], f"Health pct mismatch at frame {i}"

        # 3. Model 3 (Fault Classification)
        fault_before = pred_before["fault_classification"]
        fault_after = pred_after["fault_classification"]
        assert fault_before["predicted_fault"] == fault_after["predicted_fault"], f"Fault label mismatch at frame {i}"
        assert fault_before["confidence"] == fault_after["confidence"], f"Fault confidence mismatch at frame {i}"
        assert fault_before["fault_probabilities"] == fault_after["fault_probabilities"], f"Fault probabilities mismatch at frame {i}"

        # 4. Model 4 (RUL Prediction)
        rul_before = pred_before["rul_prediction"]
        rul_after = pred_after["rul_prediction"]
        assert rul_before["status"] == rul_after["status"], f"RUL status mismatch at frame {i}"
        assert rul_before["predicted_rul_hours"] == rul_after["predicted_rul_hours"], f"Predicted RUL mismatch at frame {i}"
        if rul_before["status"] == "PREDICTED":
            assert rul_before["raw_rul_hours"] == rul_after["raw_rul_hours"], f"Raw RUL mismatch at frame {i}"
            assert rul_before["uncertainty_std_hours"] == rul_after["uncertainty_std_hours"], f"Uncertainty mismatch at frame {i}"
            assert rul_before["confidence_interval_90pct"] == rul_after["confidence_interval_90pct"], f"Confidence interval mismatch at frame {i}"

        # Overall Status
        assert pred_before["status"] == pred_after["status"], f"Overall status mismatch at frame {i}"

    logger.info(f"VERIFIED {num_test_frames} FRAMES OF FLIGHT TELEMETRY:")
    logger.info("  [✓] Model 1 Anomaly: 100% Bitwise Identical (anomaly_score, is_anomaly, decision_function)")
    logger.info("  [✓] Model 2 Degradation: 100% Bitwise Identical (degradation_index, estimated_health_pct)")
    logger.info("  [✓] Model 3 Fault Classification: 100% Bitwise Identical (predicted_fault, confidence, class_probabilities)")
    logger.info("  [✓] Model 4 RUL Estimation: 100% Bitwise Identical (raw_rul_hours, predicted_rul_hours, uncertainty_std_hours)")
    logger.info("  [✓] XAI is 100% Observational - Zero Side-Effects on Frozen ML Models or Predictions!")
    logger.info("==================================================================")
    logger.info("REGRESSION TEST PASSED SUCCESSFULLY!")
    logger.info("==================================================================")

if __name__ == "__main__":
    run_regression_test()
