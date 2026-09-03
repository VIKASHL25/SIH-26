import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from backend.security import verify_internal_key
from explainability.xai_engine import DigitalTwinXAIEngine
from backend.model_loader import DigitalTwinModelManager

from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("XAIAdvisoryMicroservice")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Global instances
model_manager = DigitalTwinModelManager()
xai_engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global xai_engine
    try:
        model_manager.load_all_models()
        xai_engine = DigitalTwinXAIEngine()
        xai_engine.initialize(model_manager)
        logger.info("DigitalTwinXAIEngine initialized in XAI Microservice.")
    except Exception as e:
        logger.error(f"XAI initialization error: {e}")
    yield

app = FastAPI(
    title="Digital Twin XAI & Advisory Service",
    description="Microservice computing SHAP feature attributions, diagnostic drivers, engineering assessments, and maintenance action advisories.",
    version="1.0.0",
    lifespan=lifespan
)

class ExplainReq(BaseModel):
    feature_vectors: Dict[str, Any]
    predictions: Dict[str, Any]

@app.get("/health")
def get_health():
    return {
        "service": "XAI & Advisory Microservice",
        "status": "HEALTHY" if xai_engine is not None and xai_engine._initialized else "INITIALIZING"
    }

@app.post("/explain", dependencies=[Depends(verify_internal_key)])
def explain_diagnostic(req: ExplainReq):
    if xai_engine is None:
        raise HTTPException(status_code=500, detail="XAI Engine not initialized")
    
    try:
        explanation = xai_engine.explain(
            feature_vectors=req.feature_vectors,
            predictions=req.predictions,
            model_manager=model_manager
        )
        return explanation
    except Exception as e:
        logger.error(f"XAI computation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
