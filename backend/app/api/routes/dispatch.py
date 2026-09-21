from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional
from app.schemas.dispatch import DispatchStatusUpdate, DispatchResponse
from app.services.dispatch_service import dispatch_service

router = APIRouter()


@router.post("/dispatch/incident/{incident_id}", summary="Trigger Automatic Rescue Unit Dispatch")
async def trigger_dispatch(incident_id: str):
    """
    Find nearest suitable available rescue unit via Haversine distance, calculate AI emergency route,
    and assign dispatch mission for the given incident ID or incident code.
    """
    try:
        result = dispatch_service.dispatch_incident(incident_id)
        return result
    except ValueError as e:
        msg = str(e)
        if "already has an active dispatch" in msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"success": False, "status": "ALREADY_DISPATCHED", "message": msg})
        elif "No available rescue unit" in msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"success": False, "status": "NO_AVAILABLE_UNIT", "message": msg})
        elif "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"success": False, "status": "INCIDENT_NOT_FOUND", "message": msg})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"success": False, "status": "DISPATCH_FAILED", "message": msg})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"success": False, "status": "DISPATCH_ERROR", "message": str(e)})


@router.get("/dispatches", summary="List Dispatch Missions")
async def list_dispatches(
    status: Optional[str] = Query(None, description="Filter dispatches by status (e.g. DISPATCHED, EN_ROUTE, ON_SCENE, COMPLETED)")
):
    """
    Retrieve list of dispatch missions with optional status query filter.
    """
    return dispatch_service.list_dispatches(status=status)


@router.get("/dispatches/{dispatch_id}", summary="Get Dispatch Mission Details")
async def get_dispatch(dispatch_id: str):
    """
    Retrieve single dispatch mission by ID.
    """
    item = dispatch_service.get_dispatch(dispatch_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dispatch mission '{dispatch_id}' not found.")
    return item


@router.patch("/dispatches/{dispatch_id}/status", summary="Update Dispatch Mission Status")
async def update_dispatch_status(dispatch_id: str, payload: DispatchStatusUpdate):
    """
    Update dispatch mission state (DISPATCHED -> EN_ROUTE -> ON_SCENE -> COMPLETED / CANCELLED).
    Synchronizes rescue unit and incident statuses accordingly.
    """
    try:
        updated = dispatch_service.update_dispatch_status(dispatch_id, payload.status)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"success": False, "status": "INVALID_TRANSITION", "message": str(e)})
