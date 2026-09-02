import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from backend.security import verify_internal_key
from backend.simulation_engine import MissionSimulationEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TelemetryMicroservice")

app = FastAPI(
    title="Digital Twin Telemetry & Simulation Service",
    description="Ingests engine telemetry, computes thermodynamic physics residuals, and manages mission playback.",
    version="1.0.0"
)

# Global simulation engine instance
sim_engine = MissionSimulationEngine()

@app.on_event("startup")
def startup_event():
    try:
        sim_engine.initialize()
        logger.info("Telemetry Simulation Engine initialized successfully.")
    except Exception as e:
        logger.error(f"Telemetry engine initialization error: {e}")

class LoadMissionReq(BaseModel):
    mission_id: int

class SpeedReq(BaseModel):
    speed: float

class SeekReq(BaseModel):
    frame_idx: int

class FaultInjectReq(BaseModel):
    overrides: Dict[str, float]

@app.get("/health")
def get_health():
    return {
        "service": "Telemetry & Simulation Microservice",
        "status": "HEALTHY" if sim_engine.mission_df is not None else "INITIALIZING",
        "active_mission_id": sim_engine.active_mission_id,
        "simulation_state": sim_engine.state,
        "active_speed": sim_engine.speed
    }

@app.get("/missions", dependencies=[Depends(verify_internal_key)])
def list_missions():
    return {
        "available_mission_ids": sim_engine.get_available_missions(),
        "active_mission_id": sim_engine.active_mission_id
    }

@app.post("/load_mission", dependencies=[Depends(verify_internal_key)])
def load_mission(req: LoadMissionReq):
    try:
        sim_engine.load_mission(req.mission_id)
        return {
            "message": f"Successfully loaded Mission {req.mission_id}",
            "active_mission_id": sim_engine.active_mission_id,
            "total_frames": len(sim_engine.mission_df)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/start", dependencies=[Depends(verify_internal_key)])
def start_simulation():
    sim_engine.set_state("RUNNING")
    return {"message": "Simulation started", "state": sim_engine.state}

@app.post("/pause", dependencies=[Depends(verify_internal_key)])
def pause_simulation():
    sim_engine.set_state("PAUSED")
    return {"message": "Simulation paused", "state": sim_engine.state}

@app.post("/step", dependencies=[Depends(verify_internal_key)])
def step_simulation():
    if sim_engine.mission_df is None:
        raise HTTPException(status_code=400, detail="No active mission loaded")
    
    payload = sim_engine.step()
    if payload is None:
        raise HTTPException(status_code=400, detail="End of mission reached")
    
    return payload

@app.post("/speed", dependencies=[Depends(verify_internal_key)])
def set_speed(req: SpeedReq):
    sim_engine.set_speed(req.speed)
    return {"message": f"Speed set to {sim_engine.speed}x", "speed": sim_engine.speed}

@app.post("/seek", dependencies=[Depends(verify_internal_key)])
def seek_frame(req: SeekReq):
    sim_engine.seek(req.frame_idx)
    return {"message": f"Seeked to frame {sim_engine.current_frame_idx}", "frame_index": sim_engine.current_frame_idx}

@app.post("/inject_fault", dependencies=[Depends(verify_internal_key)])
def inject_fault(req: FaultInjectReq):
    sim_engine.set_fault_injection(req.overrides)
    return {"message": "Synthetic fault parameters injected", "active_overrides": sim_engine.fault_overrides}

@app.post("/clear_faults", dependencies=[Depends(verify_internal_key)])
def clear_faults():
    sim_engine.clear_fault_injection()
    return {"message": "Fault injection cleared"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
