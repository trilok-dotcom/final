from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.api import websocket
from app.api.routes import (
    health,
    routing,
    incidents,
    rescue_units,
    dispatch,
    mission_tracking,
    resource_optimization,
    predict,
    road_network,
    ai_detect,
    ai_routing,
    rerouting,
    command_center,
    simulation,
    evaluation,
)
from app.services.ai_service import init_road_predictor
from app.db.database import init_db
from ai.config import AI_DIR
from ai.predict import predictor
from app.utils.logging import get_logger

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database & Load U-Net AI Model
    logger.info("Initializing RESQROUTE Database Persistence...")
    try:
        init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    logger.info("Initializing RESQROUTE AI Engine...")
    try:
        init_road_predictor()
        # Warm up legacy predictor if present for backward compatibility
        try:
            predictor.load_model()
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Failed to load AI model on startup: {e}")
    yield
    # Shutdown


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="RESQROUTE Emergency Response Command Center API - Stage 8B Multi-Unit Resource Optimization Engine",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS for Vite frontend development servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.override_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure outputs directory exists and mount static files route for generated AI output images
outputs_dir = AI_DIR / "outputs"
outputs_dir.mkdir(parents=True, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(outputs_dir)), name="outputs")

# Include WebSocket Router (/api/ws/missions)
app.include_router(websocket.router, prefix="/api", tags=["WebSocket Telemetry"])

# Include API Routers
app.include_router(ai_detect.router, prefix="/api/ai", tags=["AI Road Detection"])
app.include_router(ai_detect.router, prefix=f"{settings.API_V1_STR}/ai", tags=["AI Road Detection"])

app.include_router(ai_routing.router, prefix="/api/ai", tags=["AI Emergency Routing"])
app.include_router(ai_routing.router, prefix=f"{settings.API_V1_STR}/ai", tags=["AI Emergency Routing"])

# Mount Incidents, Rescue Units, Automatic Dispatch, Mission Tracking, and Resource Optimization under /api and /api/v1
app.include_router(incidents.router, prefix="/api", tags=["Incidents"])
app.include_router(incidents.router, prefix=settings.API_V1_STR, tags=["Incidents"])

app.include_router(rescue_units.router, prefix="/api", tags=["Rescue Units"])
app.include_router(rescue_units.router, prefix=settings.API_V1_STR, tags=["Rescue Units"])

app.include_router(dispatch.router, prefix="/api", tags=["Automatic Dispatch"])
app.include_router(dispatch.router, prefix=settings.API_V1_STR, tags=["Automatic Dispatch"])

app.include_router(mission_tracking.router, prefix="/api", tags=["Mission Tracking"])
app.include_router(mission_tracking.router, prefix=settings.API_V1_STR, tags=["Mission Tracking"])

app.include_router(resource_optimization.router, prefix="/api", tags=["Resource Optimization"])
app.include_router(resource_optimization.router, prefix=settings.API_V1_STR, tags=["Resource Optimization"])

app.include_router(rerouting.router, prefix="/api", tags=["Dynamic Rerouting"])
app.include_router(rerouting.router, prefix=settings.API_V1_STR, tags=["Dynamic Rerouting"])

app.include_router(command_center.router, prefix="/api", tags=["Disaster Command Center"])
app.include_router(command_center.router, prefix=settings.API_V1_STR, tags=["Disaster Command Center"])

app.include_router(simulation.router, prefix="/api", tags=["Disaster Simulation System"])
app.include_router(simulation.router, prefix=settings.API_V1_STR, tags=["Disaster Simulation System"])

app.include_router(evaluation.router, prefix="/api", tags=["System Evaluation"])
app.include_router(evaluation.router, prefix=settings.API_V1_STR, tags=["System Evaluation"])

app.include_router(health.router, prefix=settings.API_V1_STR, tags=["Health"])
app.include_router(routing.router, prefix=settings.API_V1_STR, tags=["Routing"])
app.include_router(predict.router, prefix=settings.API_V1_STR, tags=["AI Prediction"])
app.include_router(road_network.router, prefix=settings.API_V1_STR, tags=["Road Network"])


@app.get("/")
async def root():
    return {
        "project": "RESQROUTE Emergency Response Platform",
        "api_docs": "/docs",
        "websocket": "/api/ws/missions",
        "incidents_api": "/api/incidents",
        "rescue_units_api": "/api/rescue-units",
        "dispatch_api": "/api/dispatch/incident/{incident_id}",
        "live_mission": "/api/dispatches/{dispatch_id}/live",
        "optimize_resources": "/api/incidents/{incident_id}/optimize-resources",
        "dispatch_optimized": "/api/incidents/{incident_id}/dispatch-optimized",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
