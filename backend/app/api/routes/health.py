from fastapi import APIRouter
from app.services.ai_service import get_road_predictor

router = APIRouter()

@router.get("/health", summary="Health Check")
async def health_check():
    model_loaded = False
    device_name = "unknown"
    try:
        predictor = get_road_predictor()
        model_loaded = predictor.detector.model is not None
        device_name = str(predictor.device)
    except Exception:
        pass

    return {
        "status": "ok",
        "service": "RESQROUTE Emergency Response Platform API",
        "version": "1.0.0",
        "model_loaded": model_loaded,
        "device": device_name,
        "database": "ok",
    }
