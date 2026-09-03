import os
import sys
from contextlib import asynccontextmanager

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import logging
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from backend.security import verify_internal_key
from backend.simulation_engine import MissionSimulationEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TelemetryMicroservice")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Global simulation engine instance
sim_engine = MissionSimulationEngine()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        sim_engine.initialize()
        logger.info("Telemetry Simulation Engine initialized successfully.")
    except Exception as e:
        logger.error(f"Telemetry engine initialization error: {e}")
    yield
    try:
        sim_engine.close()
        logger.info("Telemetry Simulation Engine closed cleanly.")
    except Exception:
        pass

app = FastAPI(
    title="Digital Twin Telemetry & Simulation Service",
    description="Ingests engine telemetry, computes thermodynamic physics residuals, and manages mission playback.",
    version="1.0.0",
    lifespan=lifespan
)

class LoadMissionReq(BaseModel):
    mission_id: int

class SpeedReq(BaseModel):
    speed: float

class SeekReq(BaseModel):
    frame_idx: int

class FaultInjectReq(BaseModel):
    overrides: Dict[str, float]

class ScenarioReq(BaseModel):
    scenario_name: Optional[str] = "high_altitude"
    altitude_m: Optional[float] = None
    ambient_temp_C: Optional[float] = None
    throttle_profile: Optional[List[float]] = None
    duration_steps: Optional[int] = 30

@app.get("/health")
def get_health():
    return {
        "service": "Telemetry & Simulation Microservice",
        "status": "HEALTHY" if sim_engine.mission_df is not None else "INITIALIZING",
        "active_mission_id": sim_engine.active_mission_id,
        "simulation_state": sim_engine.state,
        "active_speed": sim_engine.speed
    }

@app.get("/status", dependencies=[Depends(verify_internal_key)])
def get_simulation_status():
    """Lightweight endpoint returning current simulation state and speed without re-evaluating frame physics."""
    return {
        "status": "HEALTHY" if sim_engine.mission_df is not None else "INITIALIZING",
        "simulation_state": sim_engine.state,
        "playback_state": sim_engine.state,
        "playback_speed": sim_engine.speed,
        "speed": sim_engine.speed,
        "active_mission_id": sim_engine.active_mission_id,
        "current_frame_idx": sim_engine.current_frame_idx,
        "total_frames": len(sim_engine.mission_df) if sim_engine.mission_df is not None else 0
    }

@app.get("/current_frame", dependencies=[Depends(verify_internal_key)])
def get_current_frame():
    """Evaluates and returns current frame without advancing index."""
    if sim_engine.mission_df is None:
        raise HTTPException(status_code=400, detail="No active mission loaded")
    payload = sim_engine.get_current_frame()
    if payload is None:
        raise HTTPException(status_code=400, detail="End of mission reached")
    return payload

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
def step_simulation(force: bool = False):
    if sim_engine.mission_df is None:
        raise HTTPException(status_code=400, detail="No active mission loaded")
    
    # Only advance frame if simulation is RUNNING, or if explicitly forced by manual step
    should_advance = (sim_engine.state == "RUNNING") or force
    if not should_advance:
        return {
            "playback_state": sim_engine.state,
            "simulation_state": sim_engine.state,
            "playback_speed": sim_engine.speed,
            "active_mission_id": sim_engine.active_mission_id,
            "frame_index": sim_engine.current_frame_idx,
            "total_frames": len(sim_engine.mission_df)
        }
        
    payload = sim_engine.step(advance=True)
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
    return {"message": "Fault overrides cleared"}

@app.post("/simulate/scenario", dependencies=[Depends(verify_internal_key)])
def simulate_scenario(req: ScenarioReq):
    try:
        res = sim_engine.simulate_scenario(
            scenario_name=req.scenario_name or "high_altitude",
            altitude_m=req.altitude_m,
            ambient_temp_C=req.ambient_temp_C,
            throttle_profile=req.throttle_profile,
            duration_steps=req.duration_steps or 30
        )
        return res
    except Exception as e:
        logger.error(f"Scenario simulation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

