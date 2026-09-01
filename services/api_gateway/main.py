import asyncio
import logging
import os
import sys
from typing import Dict, Any, Optional, List
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("APIGateway")

app = FastAPI(
    title="MALE UAV Digital Twin API Gateway",
    description="Central Microservices Gateway & WebSocket Proxy for GCS Dashboard Health Monitoring, Predictive Analytics & MongoDB Atlas Persistence.",
    version="2.0.0"
)

# Enable CORS for GCS / Web Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Microservices URLs
TELEMETRY_SERVICE_URL = os.getenv("TELEMETRY_SERVICE_URL", "http://localhost:8001")
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://localhost:8002")
XAI_SERVICE_URL = os.getenv("XAI_SERVICE_URL", "http://localhost:8003")
MONGO_SERVICE_URL = os.getenv("MONGO_SERVICE_URL", "http://localhost:8004")

# Pydantic Schemas
class LoadMissionReq(BaseModel):
    mission_id: int

class SpeedReq(BaseModel):
    speed: float

class SeekReq(BaseModel):
    frame_idx: int

class FaultInjectReq(BaseModel):
    overrides: Dict[str, float]

async def enrich_and_persist_telemetry(client: httpx.AsyncClient, payload: dict) -> dict:
    """
    Enriches raw telemetry payload via ML Inference & XAI Advisory microservices,
    and automatically persists frame telemetry logs to MongoDB Atlas.
    """
    feature_vectors = payload.get("feature_vectors")
    
    # Query ML Inference Service (Port 8002) if models_prediction not already computed
    if feature_vectors and "models_prediction" not in payload:
        try:
            ml_res = await client.post(
                f"{ML_SERVICE_URL}/predict_all",
                json={
                    "feature_vectors": feature_vectors,
                    "buffer_len": payload.get("buffer_length", 13)
                }
            )
            if ml_res.status_code == 200:
                ml_data = ml_res.json()
                payload["models_prediction"] = ml_data
                payload["health_status"] = ml_data.get("status", payload.get("health_status", "NOMINAL"))
                payload["anomaly_detection"] = ml_data.get("anomaly_detection")
                payload["degradation_estimation"] = ml_data.get("degradation_estimation")
                payload["fault_classification"] = ml_data.get("fault_classification")
                payload["rul_prediction"] = ml_data.get("rul_prediction")
        except Exception as e:
            logger.error(f"ML Microservice query error: {e}")

    # Query XAI Advisory Service (Port 8003) for SHAP explainability
    clean_sample = payload.get("clean_sample")
    predictions = payload.get("models_prediction")
    if clean_sample and predictions and ("xai_explanation" not in payload and "xai" not in payload):
        try:
            xai_res = await client.post(
                f"{XAI_SERVICE_URL}/explain",
                json={"clean_sample": clean_sample, "predictions": predictions}
            )
            if xai_res.status_code == 200:
                xai_data = xai_res.json()
                payload["xai_explanation"] = xai_data
                payload["xai"] = xai_data
                payload["advisories"] = xai_data.get("advisories", [])
        except Exception as e:
            logger.error(f"XAI Microservice query error: {e}")

    # Async log frame payload to MongoDB Persistence Service (Port 8004)
    if "telemetry" in payload and "degradation_estimation" in payload:
        try:
            db_log_data = {
                "mission_id": payload.get("mission_id", 1),
                "frame_index": payload.get("frame_index", 0),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "telemetry": payload.get("telemetry", {}),
                "physics_residuals": payload.get("physics_model", {}),
                "predictions": {
                    "anomaly": payload.get("anomaly_detection", {}),
                    "degradation": payload.get("degradation_estimation", {}),
                    "fault": payload.get("fault_classification", {}),
                    "rul": payload.get("rul_prediction", {})
                },
                "xai_drivers": (payload.get("xai") or payload.get("xai_explanation", {})).get("top_diagnostic_drivers", []),
                "advisories": payload.get("advisories", [])
            }
            await client.post(f"{MONGO_SERVICE_URL}/log_telemetry", json=db_log_data, timeout=1.0)
        except Exception as e:
            logger.debug(f"MongoDB logging error: {e}")

    return payload

@app.get("/")
def read_root():
    return {
        "system": "MALE UAV Aero Piston Engine Digital Twin Framework",
        "architecture": "MICROSERVICES_GATEWAY_WITH_MONGODB_ATLAS",
        "services": {
            "telemetry_simulation_service": TELEMETRY_SERVICE_URL,
            "ml_inference_service": ML_SERVICE_URL,
            "xai_advisory_service": XAI_SERVICE_URL,
            "mongodb_persistence_service": MONGO_SERVICE_URL
        }
    }

@app.get("/api/health")
async def get_health():
    async with httpx.AsyncClient() as client:
        try:
            t_res = await client.get(f"{TELEMETRY_SERVICE_URL}/health", timeout=3.0)
            m_res = await client.get(f"{ML_SERVICE_URL}/health", timeout=3.0)
            x_res = await client.get(f"{XAI_SERVICE_URL}/health", timeout=3.0)
            db_res = await client.get(f"{MONGO_SERVICE_URL}/health", timeout=3.0)

            t_data = t_res.json() if t_res.status_code == 200 else {"status": "OFFLINE"}
            m_data = m_res.json() if m_res.status_code == 200 else {"status": "OFFLINE"}
            x_data = x_res.json() if x_res.status_code == 200 else {"status": "OFFLINE"}
            db_data = db_res.json() if db_res.status_code == 200 else {"status": "OFFLINE"}

            overall = "HEALTHY" if (t_data.get("status") == "HEALTHY" and m_data.get("status") == "HEALTHY" and x_data.get("status") == "HEALTHY" and db_data.get("status") == "HEALTHY") else "DEGRADED"

            return {
                "status": overall,
                "services": {
                    "telemetry": t_data,
                    "ml_inference": m_data,
                    "xai_advisory": x_data,
                    "mongodb_atlas": db_data
                }
            }
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}

@app.get("/api/missions")
async def list_missions():
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{TELEMETRY_SERVICE_URL}/missions")
        return res.json()

@app.post("/api/simulation/load_mission")
async def load_mission(req: LoadMissionReq):
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{TELEMETRY_SERVICE_URL}/load_mission", json=req.model_dump())
        await client.post(f"{ML_SERVICE_URL}/reset_state")
        return res.json()

@app.post("/api/simulation/start")
async def start_simulation():
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{TELEMETRY_SERVICE_URL}/start")
        return res.json()

@app.post("/api/simulation/pause")
async def pause_simulation():
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{TELEMETRY_SERVICE_URL}/pause")
        return res.json()

@app.post("/api/simulation/step")
async def step_simulation():
    async with httpx.AsyncClient() as client:
        t_res = await client.post(f"{TELEMETRY_SERVICE_URL}/step")
        if t_res.status_code != 200:
            raise HTTPException(status_code=t_res.status_code, detail=t_res.text)
        payload = t_res.json()
        enriched = await enrich_and_persist_telemetry(client, payload)
        return enriched

@app.post("/api/simulation/speed")
async def set_speed(req: SpeedReq):
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{TELEMETRY_SERVICE_URL}/speed", json=req.model_dump())
        return res.json()

@app.post("/api/simulation/seek")
async def seek_frame(req: SeekReq):
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{TELEMETRY_SERVICE_URL}/seek", json=req.model_dump())
        return res.json()

@app.post("/api/simulation/inject_fault")
async def inject_fault(req: FaultInjectReq):
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{TELEMETRY_SERVICE_URL}/inject_fault", json=req.model_dump())
        return res.json()

@app.post("/api/simulation/clear_faults")
async def clear_faults():
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{TELEMETRY_SERVICE_URL}/clear_faults")
        return res.json()

# MongoDB Gateway Endpoints
@app.get("/api/db/saved_missions")
async def get_saved_missions():
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{MONGO_SERVICE_URL}/list_saved_missions")
        return res.json()

@app.get("/api/db/fleet_metadata")
async def get_fleet_metadata():
    """Fleet Metadata Endpoint: Returns tail numbers, flight hours, and depot maintenance history."""
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{MONGO_SERVICE_URL}/get_fleet_metadata")
        return res.json()

@app.get("/api/db/mission/{mission_id}/replay")
async def get_mission_replay(mission_id: int):
    """Mission Replay Endpoint: Fetches logged telemetry trajectory from MongoDB Atlas."""
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{MONGO_SERVICE_URL}/mission_replay/{mission_id}")
        return res.json()

@app.get("/api/db/advisories")
async def get_advisories(mission_id: Optional[int] = None):
    async with httpx.AsyncClient() as client:
        url = f"{MONGO_SERVICE_URL}/get_advisories"
        if mission_id is not None:
            url += f"?mission_id={mission_id}"
        res = await client.get(url)
        return res.json()

@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """
    Real-Time WebSocket Stream connecting GCS Dashboard to Microservices Pipeline & MongoDB.
    """
    await websocket.accept()
    logger.info("Client connected to API Gateway WebSocket Stream.")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            while True:
                t_res = await client.post(f"{TELEMETRY_SERVICE_URL}/step")
                
                if t_res.status_code == 200:
                    payload = t_res.json()
                    sim_state = payload.get("simulation_state", "PAUSED")
                    speed = payload.get("simulation_speed", 1.0)
                    delay_s = max(0.1, 1.0 / max(0.1, float(speed)))

                    if sim_state == "RUNNING":
                        enriched = await enrich_and_persist_telemetry(client, payload)
                        await websocket.send_json(enriched)
                        await asyncio.sleep(delay_s)
                    else:
                        await websocket.send_json(payload)
                        await asyncio.sleep(0.5)
                else:
                    await asyncio.sleep(0.5)

        except WebSocketDisconnect:
            logger.info("Client disconnected from API Gateway WebSocket Stream.")
        except Exception as e:
            logger.error(f"WebSocket Proxy Exception: {e}")
            try:
                await websocket.close()
            except Exception:
                pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
