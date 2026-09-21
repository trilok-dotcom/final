from fastapi import APIRouter

router = APIRouter()

@router.get("/health", summary="Health Check")
async def health_check():
    return {
        "status": "ok",
        "service": "RESQROUTE Emergency Routing Engine",
        "version": "1.0.0",
        "mode": "stage_2_osrm_active"
    }
