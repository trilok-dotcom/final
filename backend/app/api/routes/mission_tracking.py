from fastapi import APIRouter, HTTPException, status
from app.schemas.mission import LocationUpdatePayload, LiveMissionResponse
from app.services.mission_tracking_service import mission_tracking_service

router = APIRouter()


@router.post("/dispatches/{dispatch_id}/location", summary="Update Rescue Unit Live Telemetry Location")
@router.post("/missions/{dispatch_id}/location", summary="Update Rescue Unit Live Telemetry Location (Alias)")
async def update_location(dispatch_id: str, payload: LocationUpdatePayload):
    """
    Update rescue unit live latitude, longitude, speed, heading, and accuracy telemetry.
    Recalculates distance remaining, ETA, and progress percentage, and broadcasts over WebSocket.
    """
    try:
        lat = payload.get_lat()
        lng = payload.get_lng()
        accuracy = payload.get_accuracy()
        result = mission_tracking_service.update_location(
            dispatch_id=dispatch_id,
            lat=lat,
            lng=lng,
            speed_kmh=payload.speed_kmh or 0.0,
            heading_degrees=payload.heading_degrees or 0.0,
            accuracy=accuracy,
            timestamp=payload.timestamp,
        )
        return result
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@router.get("/dispatches/{dispatch_id}/live", summary="Get Live Dispatch Mission Telemetry")
@router.get("/missions/{dispatch_id}/live", summary="Get Live Dispatch Mission Telemetry (Alias)")
async def get_live_mission(dispatch_id: str):
    """
    Retrieve real-time telemetry, unit location, distance remaining, progress %, and ETA for active mission.
    """
    try:
        result = mission_tracking_service.get_live_mission(dispatch_id)
        return result
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@router.post("/dispatches/{dispatch_id}/simulate", summary="Start Live Rescue Unit Movement Simulation")
async def start_simulation(dispatch_id: str):
    """
    Start async movement simulation stepping rescue unit along stored AI route geometry coordinates.
    """
    try:
        result = mission_tracking_service.start_simulation(dispatch_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/dispatches/{dispatch_id}/simulation/stop", summary="Stop Live Rescue Unit Movement Simulation")
async def stop_simulation(dispatch_id: str):
    """
    Stop active movement simulation for dispatch ID.
    """
    return mission_tracking_service.stop_simulation(dispatch_id)
