import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel
from pymongo import MongoClient, DESCENDING
from dotenv import load_dotenv
from backend.security import verify_internal_key

from contextlib import asynccontextmanager

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MongoDBMicroservice")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# MongoDB Connection Configuration (Loaded from .env)
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("MONGO_DB_NAME", "aero_digital_twin_db")

client: Optional[MongoClient] = None
db = None

# In-Memory Fallback Store (active when MongoDB Atlas is offline)
in_memory_telemetry_logs: Dict[str, Dict[str, Any]] = {}
in_memory_summaries: Dict[int, Dict[str, Any]] = {}
in_memory_advisories: List[Dict[str, Any]] = []
in_memory_fleet: List[Dict[str, Any]] = [{
    "engine_serial_number": "ENG-MALE-UAV-2026-99",
    "uav_tail_number": "TAPAS-BH-201",
    "total_operating_hours": 487.50,
    "accumulated_missions_count": 48,
    "current_engine_health_pct": 95.33,
    "last_depot_overhaul": "2026-07-15",
    "status": "AIRWORTHY"
}]

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, db
    try:
        logger.info(f"Connecting to MongoDB Atlas database: {DB_NAME}...")
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
        client.admin.command('ping')
        db = client[DB_NAME]
        logger.info("Successfully connected to MongoDB Atlas!")
        
        # Create Indexes for fast querying & Mission Replay
        db["mission_telemetry_logs"].create_index([("mission_id", 1), ("frame_index", 1)])
        db["mission_telemetry_logs"].create_index([("timestamp", -1)])
        db["mission_summaries"].create_index([("mission_id", 1)], unique=True)
        db["advisory_history"].create_index([("timestamp", -1)])
        db["fault_injection_logs"].create_index([("timestamp", -1)])
        db["engine_fleet_metadata"].create_index([("engine_serial_number", 1)], unique=True)
        
        # Seed default Engine Fleet Metadata if empty
        if db["engine_fleet_metadata"].count_documents({}) == 0:
            db["engine_fleet_metadata"].insert_one(in_memory_fleet[0])
            logger.info("Seeded engine fleet metadata for TAPAS-BH-201.")
        
    except Exception as e:
        logger.warning(f"MongoDB Atlas unavailable ({e}). Fallback to local in-memory storage mode.")
        db = None
    yield
    if client:
        client.close()
        logger.info("MongoDB client connection closed.")

app = FastAPI(
    title="Digital Twin MongoDB Persistence Service",
    description="Microservice for persisting engine telemetry logs, mission summaries, advisories, fault injection logs, and engine fleet metadata to MongoDB Atlas.",
    version="1.0.0",
    lifespan=lifespan
)

# Pydantic Schemas matching exact collection structures
class TelemetryLogReq(BaseModel):
    mission_id: int
    frame_index: int
    timestamp: Optional[str] = None
    telemetry: Dict[str, Any]
    physics_residuals: Dict[str, Any]
    predictions: Dict[str, Any]
    xai_drivers: Optional[List[Dict[str, Any]]] = []
    advisories: Optional[List[str]] = []

class MissionSummaryReq(BaseModel):
    mission_id: int
    total_frames: int
    start_timestamp: str
    end_timestamp: str
    max_cht_C: float
    max_egt_C: float
    min_oil_pressure_bar: float
    initial_health_pct: float
    final_health_pct: float
    final_rul_hours: Optional[float] = None
    total_anomalies_detected: int = 0
    total_faults_classified: int = 0
    overall_mission_status: str = "COMPLETED"

class AdvisoryLogReq(BaseModel):
    mission_id: int
    frame_index: int
    alert_type: str
    health_index_pct: float
    predicted_rul_hours: Optional[float] = None
    message: str
    recommended_action: str

class FaultLogReq(BaseModel):
    mission_id: int
    frame_index: int
    injected_overrides: Dict[str, float]
    detected_status: str
    classified_fault: str

@app.get("/health")
def get_health():
    is_connected = False
    if client and db is not None:
        try:
            client.admin.command('ping')
            is_connected = True
        except Exception:
            is_connected = False
            
    return {
        "service": "MongoDB Persistence Microservice",
        "status": "HEALTHY",
        "database_name": DB_NAME,
        "storage_mode": "ATLAS" if is_connected else "IN_MEMORY_FALLBACK",
        "atlas_connected": is_connected
    }

@app.post("/log_telemetry", dependencies=[Depends(verify_internal_key)])
def log_telemetry(data: TelemetryLogReq):
    doc = data.model_dump()
    if not doc.get("timestamp"):
        doc["timestamp"] = datetime.now(timezone.utc).isoformat()
    
    if db is not None:
        try:
            db["mission_telemetry_logs"].update_one(
                {"mission_id": data.mission_id, "frame_index": data.frame_index},
                {"$set": doc},
                upsert=True
            )
            return {"status": "SUCCESS", "mission_id": data.mission_id, "frame_index": data.frame_index}
        except Exception as e:
            logger.error(f"Error logging telemetry to MongoDB: {e}")
            
    # In-Memory Fallback
    key = f"{data.mission_id}_{data.frame_index}"
    in_memory_telemetry_logs[key] = doc
    return {"status": "SUCCESS", "mission_id": data.mission_id, "frame_index": data.frame_index, "storage": "in_memory"}

@app.get("/mission_replay/{mission_id}", dependencies=[Depends(verify_internal_key)])
def get_mission_replay(mission_id: int, limit: int = Query(2000, le=10000)):
    if db is not None:
        try:
            cursor = db["mission_telemetry_logs"].find(
                {"mission_id": mission_id},
                {"_id": 0}
            ).sort("frame_index", 1).limit(limit)
            
            frames = list(cursor)
            summary = db["mission_summaries"].find_one({"mission_id": mission_id}, {"_id": 0})
            
            return {
                "mission_id": mission_id,
                "total_recorded_frames": len(frames),
                "summary": summary,
                "frames": frames
            }
        except Exception as e:
            logger.error(f"Error fetching mission replay from MongoDB: {e}")

    # In-Memory Fallback Query
    matched_frames = [
        doc for key, doc in in_memory_telemetry_logs.items()
        if doc.get("mission_id") == mission_id
    ]
    matched_frames.sort(key=lambda x: x.get("frame_index", 0))
    frames = matched_frames[:limit]
    summary = in_memory_summaries.get(mission_id)

    return {
        "mission_id": mission_id,
        "total_recorded_frames": len(frames),
        "summary": summary,
        "frames": frames
    }

@app.get("/list_saved_missions", dependencies=[Depends(verify_internal_key)])
def list_saved_missions():
    if db is not None:
        try:
            missions = db["mission_telemetry_logs"].distinct("mission_id")
            return {"recorded_missions": sorted(missions)}
        except Exception as e:
            logger.error(f"Error listing saved missions from MongoDB: {e}")

    # In-Memory Fallback
    missions = set(doc.get("mission_id") for doc in in_memory_telemetry_logs.values() if "mission_id" in doc)
    return {"recorded_missions": sorted(list(missions))}

@app.post("/log_summary", dependencies=[Depends(verify_internal_key)])
def log_mission_summary(data: MissionSummaryReq):
    doc = data.model_dump()
    if db is not None:
        try:
            db["mission_summaries"].update_one(
                {"mission_id": data.mission_id},
                {"$set": doc},
                upsert=True
            )
            return {"status": "SUCCESS", "mission_id": data.mission_id}
        except Exception as e:
            logger.error(f"Error logging mission summary to MongoDB: {e}")

    # In-Memory Fallback
    in_memory_summaries[data.mission_id] = doc
    return {"status": "SUCCESS", "mission_id": data.mission_id}

@app.post("/log_advisory", dependencies=[Depends(verify_internal_key)])
def log_advisory(data: AdvisoryLogReq):
    doc = data.model_dump()
    doc["timestamp"] = datetime.now(timezone.utc).isoformat()
    if db is not None:
        try:
            db["advisory_history"].insert_one(doc)
            return {"status": "SUCCESS"}
        except Exception as e:
            logger.error(f"Error logging advisory to MongoDB: {e}")

    # In-Memory Fallback
    in_memory_advisories.append(doc)
    return {"status": "SUCCESS"}

@app.get("/get_advisories", dependencies=[Depends(verify_internal_key)])
def get_advisories(mission_id: Optional[int] = None, limit: int = 100):
    if db is not None:
        try:
            query = {"mission_id": mission_id} if mission_id is not None else {}
            cursor = db["advisory_history"].find(query, {"_id": 0}).sort("timestamp", DESCENDING).limit(limit)
            return {"advisories": list(cursor)}
        except Exception as e:
            logger.error(f"Error fetching advisories from MongoDB: {e}")

    # In-Memory Fallback
    res = [a for a in in_memory_advisories if mission_id is None or a.get("mission_id") == mission_id]
    res.reverse()
    return {"advisories": res[:limit]}

@app.get("/get_fleet_metadata", dependencies=[Depends(verify_internal_key)])
def get_fleet_metadata():
    if db is not None:
        try:
            fleet = list(db["engine_fleet_metadata"].find({}, {"_id": 0}))
            return {"fleet": fleet}
        except Exception as e:
            logger.error(f"Error fetching fleet metadata from MongoDB: {e}")

    # In-Memory Fallback
    return {"fleet": in_memory_fleet}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
