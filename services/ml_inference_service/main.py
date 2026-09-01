import os
import sys
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.model_loader import DigitalTwinModelManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MLInferenceMicroservice")

app = FastAPI(
    title="Digital Twin AI/ML Inference Service",
    description="Microservice providing real-time predictions for Anomaly Detection, Degradation Estimation, Fault Classification, and RUL with Uncertainty Quantification.",
    version="1.0.0"
)

# Global Model Manager Instance
model_manager = DigitalTwinModelManager()

@app.on_event("startup")
def startup_event():
    try:
        model_manager.load_all_models()
        logger.info("All 4 AI/ML models loaded in ML Inference Microservice.")
    except Exception as e:
        logger.error(f"Failed to load AI/ML models: {e}")

class FeatureVectorsPayload(BaseModel):
    feature_vectors: Dict[str, Any]
    anomaly_threshold: Optional[float] = 0.0
    buffer_len: Optional[int] = 13

@app.get("/health")
def get_health():
    return {
        "service": "AI/ML Inference Microservice",
        "status": "HEALTHY" if model_manager._is_loaded else "INITIALIZING",
        "models_loaded": model_manager._is_loaded
    }

@app.post("/predict_all")
def predict_all(payload: FeatureVectorsPayload):
    if not model_manager._is_loaded:
        raise HTTPException(status_code=500, detail="Models not loaded")
    
    try:
        results = model_manager.predict_all(
            feature_vectors=payload.feature_vectors,
            anomaly_threshold=payload.anomaly_threshold,
            buffer_len=payload.buffer_len
        )
        return results
    except Exception as e:
        logger.error(f"Inference error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset_state")
def reset_state():
    model_manager.reset_state()
    return {"message": "RUL temporal filter state reset"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
