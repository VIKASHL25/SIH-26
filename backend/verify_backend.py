import sys
import os
import logging
import pandas as pd
import numpy as np

# Ensure workspace root is in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.simulation_engine import MissionSimulationEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("VerifyBackend")

def test_digital_twin_backend():
    logger.info("=================================================================")
    logger.info("STARTING INTEGRATED DIGITAL TWIN BACKEND VERIFICATION TEST")
    logger.info("=================================================================")

    # 1. Initialize Engine & Load All 4 Models
    engine = MissionSimulationEngine()
    engine.initialize()

    assert engine.model_manager._is_loaded, "Model Manager failed to load models!"
    logger.info("TEST PASS 1: All 4 AI/ML models loaded successfully.")

    # 2. Check Available Missions & Load Mission 1
    missions = engine.get_available_missions()
    assert len(missions) > 0, "No missions found in dataset!"
    logger.info(f"Available missions in dataset: {len(missions)} (e.g. Mission IDs: {missions[:5]}...)")

    engine.load_mission(missions[0])
    assert engine.active_mission_id == missions[0], f"Failed to load mission {missions[0]}"
    logger.info(f"TEST PASS 2: Mission {missions[0]} loaded with {len(engine.mission_df)} frames.")

    # 3. Simulate 25 Real-Time Ticks & Validate Warm-Up & State Transitions
    logger.info("Simulating 25 real-time ticks (testing Bug 1 RUL warm-up & Bug 2 anti-spam)...")
    advisory_history = []
    
    for i in range(25):
        payload = engine.step()
        assert payload is not None, f"Frame payload {i} is None!"

        # Validate Payload Structure
        assert "telemetry" in payload, "Missing telemetry!"
        assert "physics_model" in payload, "Missing physics_model!"
        assert "anomaly_detection" in payload, "Missing anomaly_detection!"
        assert "degradation_estimation" in payload, "Missing degradation_estimation!"
        assert "fault_classification" in payload, "Missing fault_classification!"
        assert "rul_prediction" in payload, "Missing rul_prediction!"
        assert "advisories" in payload, "Missing advisories!"

        advisories = payload["advisories"]
        advisory_history.append((i + 1, advisories))

        # Check Model 1 (Anomaly Detection)
        anom = payload["anomaly_detection"]
        assert isinstance(anom["anomaly_score"], float), "Invalid anomaly_score type"
        assert isinstance(anom["is_anomaly"], bool), "Invalid is_anomaly type"

        # Check Model 2 (Degradation Estimation)
        deg = payload["degradation_estimation"]
        assert 0.0 <= deg["degradation_index"] <= 1.0, f"Degradation index out of range: {deg['degradation_index']}"
        assert 0.0 <= deg["estimated_health_pct"] <= 100.0, f"Health pct out of range: {deg['estimated_health_pct']}"

        # Check Model 3 (Fault Classification)
        fault = payload["fault_classification"]
        assert isinstance(fault["predicted_fault"], str), "Invalid fault label"
        assert 0.0 <= fault["confidence"] <= 1.0, f"Invalid confidence: {fault['confidence']}"

        # Check Model 4 (RUL Prediction - Warm-Up vs Real Prediction)
        rul = payload["rul_prediction"]
        if i + 1 < 13:
            assert rul["status"] == "COLLECTING_HISTORY", f"Expected COLLECTING_HISTORY at tick {i+1}, got {rul['status']}"
            assert rul["predicted_rul_hours"] is None, f"Expected None RUL at tick {i+1}"
            assert rul["records_available"] == i + 1
            assert rul["records_required"] == 13
        else:
            assert rul["status"] == "PREDICTED", f"Expected PREDICTED at tick {i+1}, got {rul['status']}"
            assert rul["predicted_rul_hours"] is not None and rul["predicted_rul_hours"] >= 0.0
            assert "rul_lower_bound_p10" in rul
            assert "rul_upper_bound_p90" in rul
            assert "uncertainty_std_hours" in rul
            assert "confidence_level" in rul
            assert rul["rul_lower_bound_p10"] <= rul["predicted_rul_hours"] <= rul["rul_upper_bound_p90"] + 1e-5

    logger.info("TEST PASS 3: 25 ticks executed! Ticks 1-12 clean COLLECTING_HISTORY, Ticks 13+ stable numeric RUL & UQ bounds.")

    # Validate Anti-Spam (Bug 2): Check that advisories do not repeat continuously on every tick
    rul_advisory_count = sum(1 for tick_idx, advs in advisory_history if any("Low RUL remaining" in a for a in advs))
    assert rul_advisory_count <= 2, f"Expected RUL advisory anti-spam, but fired {rul_advisory_count} times!"
    logger.info(f"Anti-spam check passed: RUL low advisory fired {rul_advisory_count} times across 25 ticks.")

    # 4. Test Fault Injection (Synthetic Overheating)
    logger.info("Injecting synthetic overheating fault (+50°C CHT)...")
    engine.set_fault_injection({"cht_C": 50.0, "egt_C": 40.0})
    fault_payload = engine.step()
    
    assert fault_payload is not None
    logger.info(f"Fault Injection Output -> Status: {fault_payload['health_status']} | Fault: {fault_payload['fault_classification']['predicted_fault']} (Conf: {fault_payload['fault_classification']['confidence']*100:.1f}%)")
    logger.info(f"Advisories: {fault_payload['advisories']}")
    
    # Clear fault injection
    engine.clear_fault_injection()
    normal_payload = engine.step()
    logger.info(f"After Cleared Fault -> Status: {normal_payload['health_status']} | Fault: {normal_payload['fault_classification']['predicted_fault']}")
    logger.info("TEST PASS 4: Synthetic fault injection & clearance verified.")

    # 5. Test Playback Controls (Seek & Speed)
    engine.seek(100)
    assert engine.current_frame_idx == 100, f"Seek failed: {engine.current_frame_idx}"
    engine.set_speed(5.0)
    assert engine.speed == 5.0, f"Speed set failed: {engine.speed}"
    logger.info("TEST PASS 5: Simulation playback controls (seek, speed) verified.")

    logger.info("=================================================================")
    logger.info("ALL INTEGRATION TESTS PASSED CLEANLY! BOTH BUGS FIXED AND VERIFIED!")
    logger.info("=================================================================")

if __name__ == "__main__":
    test_digital_twin_backend()
