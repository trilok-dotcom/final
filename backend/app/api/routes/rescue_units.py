from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional
from app.schemas.rescue_unit import RescueUnitCreate, RescueUnitUpdate, RescueUnitStatusUpdate
from app.services.rescue_unit_service import rescue_unit_service

router = APIRouter()


@router.post("/rescue-units", status_code=status.HTTP_201_CREATED, summary="Create Rescue Unit")
async def create_rescue_unit(payload: RescueUnitCreate):
    """
    Create a new Rescue Unit in the dispatch network.
    """
    try:
        result = rescue_unit_service.create_rescue_unit(payload)
        return result
    except ValueError as e:
        if "already exists" in str(e):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/rescue-units", summary="List Rescue Units")
async def list_rescue_units(
    status: Optional[str] = Query(None, description="Filter by status (e.g. AVAILABLE, EN_ROUTE, ON_SCENE, OFFLINE)"),
    unit_type: Optional[str] = Query(None, description="Filter by unit type (e.g. AMBULANCE, FIRE_TRUCK, POLICE)"),
):
    """
    Retrieve list of rescue units with optional status or unit_type filters.
    """
    return rescue_unit_service.list_rescue_units(status=status, unit_type=unit_type)


@router.get("/rescue-units/{unit_id}", summary="Get Rescue Unit Details")
async def get_rescue_unit(unit_id: str):
    """
    Retrieve single rescue unit by ID or unit_code.
    """
    item = rescue_unit_service.get_rescue_unit(unit_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rescue unit '{unit_id}' not found.")
    return item


@router.patch("/rescue-units/{unit_id}", summary="Update Rescue Unit")
async def update_rescue_unit(unit_id: str, payload: RescueUnitUpdate):
    """
    Update rescue unit fields (e.g. location, crew_size, capabilities, current_incident_id).
    """
    item = rescue_unit_service.update_rescue_unit(unit_id, payload)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rescue unit '{unit_id}' not found.")
    return item


@router.patch("/rescue-units/{unit_id}/status", summary="Update Rescue Unit Status")
async def update_unit_status(unit_id: str, payload: RescueUnitStatusUpdate):
    """
    Update rescue unit status (e.g. AVAILABLE, DISPATCHED, EN_ROUTE, ON_SCENE, RETURNING, OFFLINE).
    """
    item = rescue_unit_service.update_status(unit_id, payload.status)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rescue unit '{unit_id}' not found.")
    return item


@router.delete("/rescue-units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Rescue Unit")
async def delete_rescue_unit(unit_id: str):
    """
    Delete rescue unit by ID or unit_code.
    """
    success = rescue_unit_service.delete_rescue_unit(unit_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rescue unit '{unit_id}' not found.")
    return None
