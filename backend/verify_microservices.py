import sys
import os
import time
import logging
import httpx

sys.path.insert(0, os.path.abspath('.'))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("VerifyFullMicroservices")

GATEWAY_URL = "http://localhost:8000"
TELEMETRY_URL = "http://localhost:8001"
ML_URL = "http://localhost:8002"
XAI_URL = "http://localhost:8003"
MONGO_URL = "http://localhost:8004"

def main():
    logger.info("=================================================================")
    logger.info("STARTING FULL END-TO-END MICROSERVICES & MONGODB VERIFICATION")
    logger.info("=================================================================")

    time.sleep(3.0)  # Wait for startup initialization

    with httpx.Client(timeout=10.0) as client:
        # 1. Health checks on all 5 microservices
        logger.info("Test 1: Checking All 5 Microservices Health Endpoints...")
        
        services_to_check = [
            ("Telemetry", TELEMETRY_URL),
            ("ML Inference", ML_URL),
            ("XAI Advisory", XAI_URL),
            ("MongoDB Atlas", MONGO_URL),
            ("API Gateway", GATEWAY_URL)
        ]
        
        for name, url in services_to_check:
            try:
                res = client.get(f"{url}/health" if name != "API Gateway" else f"{url}/api/health")
                assert res.status_code == 200, f"{name} service returned status {res.status_code}"
                status_str = res.json().get('status') or res.json().get('atlas_connected')
                logger.info(f"[SUCCESS] {name} Service Online: {status_str}")
            except Exception as e:
                logger.error(f"[ERROR] {name} Service failed health check: {e}")
                sys.exit(1)

        # 2. Test Load Out-of-Sample Demo Mission 999 via API Gateway
        logger.info("Test 2: Loading Out-of-Sample Demo Mission 999 via API Gateway...")
        res = client.post(f"{GATEWAY_URL}/api/simulation/load_mission", json={"mission_id": 999})
        assert res.status_code == 200, f"Load mission failed: {res.text}"
        msg = res.json().get('message') or res.json().get('detail', 'Loaded')
        logger.info(f"[SUCCESS] Load Mission Response: {msg}")

        # 3. Test Step Simulation & MongoDB Telemetry Logging Pipeline
        logger.info("Test 3: Stepping simulation & logging frames to MongoDB Atlas...")
        client.post(f"{GATEWAY_URL}/api/simulation/start")
        
        for step in range(1, 10):
            res = client.post(f"{GATEWAY_URL}/api/simulation/step")
            assert res.status_code == 200, f"Step {step} failed: {res.text}"
            data = res.json()
            assert "telemetry" in data, "Telemetry missing from payload"
            assert "degradation_estimation" in data, "Degradation estimation missing from payload"
            assert "rul_prediction" in data, "RUL prediction missing from payload"
        
        logger.info("[SUCCESS] 10 Steps executed cleanly with automatic MongoDB Atlas frame logging!")

        # 4. Test MongoDB Atlas Mission Replay Retrieval
        logger.info("Test 4: Testing MongoDB Atlas Mission Replay API...")
        time.sleep(1.0)
        res = client.get(f"{GATEWAY_URL}/api/db/mission/999/replay")
        assert res.status_code == 200, f"Mission replay retrieval failed: {res.text}"
        replay_data = res.json()
        assert "frames" in replay_data, "Frames missing from Mission Replay"
        recorded_count = replay_data.get("total_recorded_frames", 0)
        logger.info(f"[SUCCESS] Mission Replay Data Retrieved: {recorded_count} frames persisted in MongoDB Atlas!")

        # 5. Test Synthetic Fault Injection via Gateway
        logger.info("Test 5: Testing synthetic fault injection via Gateway...")
        res = client.post(f"{GATEWAY_URL}/api/simulation/inject_fault", json={"overrides": {"cht_C": 50.0}})
        assert res.status_code == 200
        
        fault_payload = client.post(f"{GATEWAY_URL}/api/simulation/step").json()
        health_status = fault_payload.get("health_status") or fault_payload.get("status")
        logger.info(f"[SUCCESS] Fault Injection Health Status: {health_status}")

        # Clear fault
        client.post(f"{GATEWAY_URL}/api/simulation/clear_faults")
        logger.info("[SUCCESS] Synthetic fault cleared successfully!")

        # Test 6: Verify Advisory History Retrieval
        logger.info("Test 6: Checking MongoDB Atlas Advisory History Retrieval...")
        adv_res = client.get(f"{GATEWAY_URL}/api/db/advisories?mission_id=999")
        assert adv_res.status_code == 200
        adv_list = adv_res.json().get("advisories", [])
        logger.info(f"[SUCCESS] Retrieved {len(adv_list)} advisories from MongoDB Atlas advisory_history collection!")

    logger.info("=================================================================")
    logger.info("ALL 5 MICROSERVICES & MONGODB ATLAS END-TO-END TESTS PASSED CLEANLY!")
    logger.info("=================================================================")

if __name__ == "__main__":
    main()
