import os
import sys
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from explainability.xai_engine import DigitalTwinXAIEngine
from backend.model_loader import DigitalTwinModelManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("XAIAdvisoryMicroservice")

app = FastAPI(
    title="Digital Twin XAI & Advisory Service",
    description="Microservice computing SHAP feature attributions, diagnostic drivers, engineering assessments, and maintenance action advisories.",
    version="1.0.0"
)

# Global instances
model_manager = DigitalTwinModelManager()
xai_engine = None

@app.on_event("startup")
def startup_event():
    global xai_engine
    try:
        model_manager.load_all_models()
        xai_engine = DigitalTwinXAIEngine(model_manager)
        logger.info("DigitalTwinXAIEngine initialized in XAI Microservice.")
    except Exception as e:
        logger.error(f"XAI initialization error: {e}")

class ExplainReq(BaseModel):
    clean_sample: Dict[str, Any]
    predictions: Dict[str, Any]

@app.get("/health")
def get_health():
    return {
        "service": "XAI & Advisory Microservice",
        "status": "HEALTHY" if xai_engine is not None else "INITIALIZING"
    }

@app.post("/explain")
def explain_diagnostic(req: ExplainReq):
    if xai_engine is None:
        raise HTTPException(status_code=500, detail="XAI Engine not initialized")
    
    try:
        explanation = xai_engine.explain_diagnostic(
            clean_sample=req.clean_sample,
            predictions=req.predictions
        )
        return explanation
    except Exception as e:
        logger.error(f"XAI computation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
