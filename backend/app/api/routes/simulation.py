from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field
from app.services.simulation_service import simulation_service
from app.utils.logging import get_logger

logger = get_logger("app.api.routes.simulation")

router = APIRouter(tags=["Disaster Simulation System"])


class BoundsSchema(BaseModel):
    north: float = 12.9800
    south: float = 12.9600
    west: float = 77.5800
    east: float = 77.6000


class CreateSimulationSchema(BaseModel):
    scenario_type: str = Field("URBAN_EARTHQUAKE", description="Scenario type: URBAN_EARTHQUAKE, URBAN_FLOOD, INDUSTRIAL_FIRE, MULTI_VEHICLE_ACCIDENT, CUSTOM")
    scale: str = Field("MEDIUM", description="Simulation scale: SMALL, MEDIUM, LARGE")
    seed: int = Field(42, description="Deterministic seed value")
    speed: int = Field(1, ge=1, le=10, description="Virtual clock speed factor (1x, 2x, 5x, 10x)")
    bounds: Optional[BoundsSchema] = None


class SpeedSchema(BaseModel):
    speed: int = Field(1, ge=1, le=10)


class StepSchema(BaseModel):
    seconds: int = Field(5, ge=1, le=60)


class TriggerEventSchema(BaseModel):
    event_type: str = Field(..., description="Event type: LOW_CONFIDENCE, HIGH_RISK, ETA_INCREASE, ROUTE_DISCONNECTED, UNIT_DEVIATION, NEW_INCIDENT")
    dispatch_id: Optional[str] = None
    incident_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@router.post("/simulations", response_model=Dict[str, Any])
def create_simulation(req: CreateSimulationSchema):
    """Create a new deterministic disaster simulation exercise session."""
    try:
        data = req.model_dump()
        sess = simulation_service.create_simulation(data)
        return {
            "success": True,
            "simulation_id": sess["id"],
            "scenario_type": sess["scenario_type"],
            "scenario_name": sess["scenario_name"],
            "scale": sess["scale"],
            "seed": sess["seed"],
            "status": sess["status"],
            "simulation": sess,
        }
    except Exception as e:
        logger.error(f"Failed to create simulation session: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/simulations", response_model=List[Dict[str, Any]])
def list_simulations():
    """List all created disaster simulation sessions."""
    return simulation_service.list_simulations()


@router.get("/simulations/{simulation_id}", response_model=Dict[str, Any])
def get_simulation(simulation_id: str = Path(..., description="Simulation Session ID")):
    """Fetch details of target simulation session."""
    sess = simulation_service.get_simulation(simulation_id)
    if not sess:
        raise HTTPException(status_code=404, detail=f"Simulation session '{simulation_id}' not found.")
    return {"success": True, "simulation": sess}


@router.get("/simulations/{simulation_id}/overview", response_model=Dict[str, Any])
def get_simulation_overview(simulation_id: str = Path(..., description="Simulation Session ID")):
    """Fetch complete Disaster Command Center overview for target simulation session."""
    try:
        return simulation_service.get_simulation_overview(simulation_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to fetch simulation overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulations/{simulation_id}/start", response_model=Dict[str, Any])
def start_simulation(simulation_id: str = Path(...)):
    """Start simulation exercise execution."""
    try:
        sess = simulation_service.start_simulation(simulation_id)
        return {"success": True, "simulation_id": simulation_id, "status": sess["status"], "simulation": sess}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/simulations/{simulation_id}/pause", response_model=Dict[str, Any])
def pause_simulation(simulation_id: str = Path(...)):
    """Pause simulation exercise execution."""
    try:
        sess = simulation_service.pause_simulation(simulation_id)
        return {"success": True, "simulation_id": simulation_id, "status": sess["status"], "simulation": sess}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/simulations/{simulation_id}/resume", response_model=Dict[str, Any])
def resume_simulation(simulation_id: str = Path(...)):
    """Resume simulation exercise execution."""
    try:
        sess = simulation_service.resume_simulation(simulation_id)
        return {"success": True, "simulation_id": simulation_id, "status": sess["status"], "simulation": sess}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/simulations/{simulation_id}/stop", response_model=Dict[str, Any])
def stop_simulation(simulation_id: str = Path(...)):
    """Stop simulation exercise execution."""
    try:
        sess = simulation_service.stop_simulation(simulation_id)
        return {"success": True, "simulation_id": simulation_id, "status": sess["status"], "simulation": sess}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/simulations/{simulation_id}/step", response_model=Dict[str, Any])
def step_simulation(simulation_id: str = Path(...), req: Optional[StepSchema] = Body(None)):
    """Advance virtual simulation clock by N seconds and process due timeline events."""
    try:
        seconds = req.seconds if req else 5
        sess = simulation_service.step_simulation(simulation_id, step_seconds=seconds)
        return {"success": True, "simulation_id": simulation_id, "status": sess["status"], "simulation_time": sess["simulation_time"], "simulation": sess}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/simulations/{simulation_id}/speed", response_model=Dict[str, Any])
def set_speed(simulation_id: str = Path(...), req: SpeedSchema = Body(...)):
    """Set virtual clock speed multiplier (1x, 2x, 5x, 10x)."""
    try:
        sess = simulation_service.set_speed(simulation_id, req.speed)
        return {"success": True, "simulation_id": simulation_id, "speed": sess["speed"], "simulation": sess}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/simulations/{simulation_id}/trigger-event", response_model=Dict[str, Any])
def trigger_event(simulation_id: str = Path(...), req: TriggerEventSchema = Body(...)):
    """Inject custom event (LOW_CONFIDENCE, HIGH_RISK, ETA_INCREASE, ROUTE_DISCONNECTED, UNIT_DEVIATION, NEW_INCIDENT)."""
    try:
        sess = simulation_service.trigger_custom_event(
            simulation_id=simulation_id,
            event_type=req.event_type,
            dispatch_id=req.dispatch_id,
            incident_id=req.incident_id,
            data=req.data,
        )
        return {"success": True, "simulation_id": simulation_id, "event_type": req.event_type, "simulation": sess}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/simulations/{simulation_id}/reset", response_model=Dict[str, Any])
def reset_simulation(simulation_id: str = Path(...)):
    """Safely reset and delete all records created for target simulation session."""
    try:
        return simulation_service.reset_simulation(simulation_id)
    except Exception as e:
        logger.error(f"Failed to reset simulation {simulation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
