import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.simulation_engine import MissionSimulationEngine

logger = logging.getLogger("DigitalTwinAPI")

app = FastAPI(
    title="Aero Piston Engine Digital Twin Backend API",
    description="Real-Time Health Monitoring, Fault Prediction, Degradation Tracking, RUL Estimation & Mission Replay System for MALE UAVs.",
    version="1.0.0"
)

# Enable CORS for GCS / Web Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Engine Instance
sim_engine = MissionSimulationEngine()

@app.on_event("startup")
def startup_event():
    """Initializes models and datasets on server startup."""
    try:
        sim_engine.initialize()
        logger.info("Digital Twin Backend Server initialized successfully.")
    except Exception as e:
        logger.error(f"Startup initialization failed: {e}")

# Pydantic Schemas
class LoadMissionRequest(BaseModel):
    mission_id: int

class StateRequest(BaseModel):
    state: str  # RUNNING, PAUSED, STOPPED

class SpeedRequest(BaseModel):
    speed: float

class SeekRequest(BaseModel):
    frame_idx: int

class FaultInjectRequest(BaseModel):
    overrides: Dict[str, float]

@app.get("/")
def read_root():
    return {
        "system": "MALE UAV Aero Piston Engine Digital Twin Framework",
        "status": "ONLINE",
        "models_integrated": [
            "1. Anomaly Detection (Isolation Forest)",
            "2. Degradation Estimation (XGBoost)",
            "3. Multiclass Fault Classification (XGBoost)",
            "4. Remaining Useful Life - RUL (XGBoost)"
        ],
        "active_mission": sim_engine.active_mission_id,
        "simulation_state": sim_engine.state
    }

@app.get("/api/health")
def get_health():
    is_ready = sim_engine.model_manager._is_loaded and (sim_engine.mission_df is not None)
    return {
        "status": "HEALTHY" if is_ready else "INITIALIZING",
        "models_loaded": sim_engine.model_manager._is_loaded,
        "active_mission_id": sim_engine.active_mission_id,
        "simulation_state": sim_engine.state,
        "active_speed": sim_engine.speed
    }

@app.get("/api/missions")
def list_missions():
    missions = sim_engine.get_available_missions()
    return {
        "total_missions": len(missions),
        "available_mission_ids": missions,
        "active_mission_id": sim_engine.active_mission_id
    }

@app.post("/api/simulation/load_mission")
def load_mission(req: LoadMissionRequest):
    try:
        sim_engine.load_mission(req.mission_id)
        return {
            "message": f"Successfully loaded Mission {req.mission_id}",
            "active_mission_id": sim_engine.active_mission_id,
            "total_frames": len(sim_engine.mission_df)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/simulation/start")
def start_simulation():
    sim_engine.set_state("RUNNING")
    return {"message": "Simulation started", "state": sim_engine.state}

@app.post("/api/simulation/pause")
def pause_simulation():
    sim_engine.set_state("PAUSED")
    return {"message": "Simulation paused", "state": sim_engine.state}

@app.post("/api/simulation/step")
def step_simulation():
    payload = sim_engine.step()
    if payload is None:
        raise HTTPException(status_code=400, detail="No active mission loaded")
    return payload

@app.post("/api/simulation/speed")
def set_speed(req: SpeedRequest):
    sim_engine.set_speed(req.speed)
    return {"message": f"Speed set to {sim_engine.speed}x", "speed": sim_engine.speed}

@app.post("/api/simulation/seek")
def seek_frame(req: SeekRequest):
    sim_engine.seek(req.frame_idx)
    return {"message": f"Seeked to frame {sim_engine.current_frame_idx}", "frame_index": sim_engine.current_frame_idx}

@app.post("/api/simulation/inject_fault")
def inject_fault(req: FaultInjectRequest):
    sim_engine.set_fault_injection(req.overrides)
    return {"message": "Synthetic fault parameters injected", "active_overrides": sim_engine.fault_overrides}

@app.post("/api/simulation/clear_faults")
def clear_faults():
    sim_engine.clear_fault_injection()
    return {"message": "Fault injection cleared"}

@app.get("/api/telemetry/latest")
def get_latest_telemetry():
    payload = sim_engine.step()
    if payload is None:
        raise HTTPException(status_code=400, detail="Simulation telemetry unavailable")
    return payload

@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """
    Real-Time WebSocket Stream broadcasting consolidated Digital Twin state payload.
    Adjusts streaming interval dynamically based on active playback speed.
    """
    await websocket.accept()
    logger.info("WebSocket Client Connected to Digital Twin Telemetry Stream.")
    try:
        while True:
            if sim_engine.state == "RUNNING":
                payload = sim_engine.step()
                if payload:
                    await websocket.send_json(payload)
                interval = max(0.02, 1.0 / max(0.1, sim_engine.speed))
                await asyncio.sleep(interval)
            else:
                await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        logger.info("WebSocket Client Disconnected.")
    except Exception as e:
        logger.error(f"WebSocket Streaming Error: {e}")
