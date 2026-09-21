from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional
from app.schemas.incident import IncidentCreate, IncidentUpdate
from app.services.incident_service import incident_service
from app.services.incident_intelligence_service import incident_intelligence_service

router = APIRouter()


@router.post("/incidents", status_code=status.HTTP_201_CREATED, summary="Create Emergency Incident")
async def create_incident(payload: IncidentCreate):
    """
    Create a new Emergency Incident in the dispatch system.
    """
    try:
        result = incident_service.create_incident(payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/incidents", summary="List Emergency Incidents")
async def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status (e.g. REPORTED, ACTIVE, RESOLVED)"),
    severity: Optional[str] = Query(None, description="Filter by severity (e.g. CRITICAL, HIGH, MEDIUM, LOW)"),
    incident_type: Optional[str] = Query(None, description="Filter by incident type (e.g. FIRE, MEDICAL, FLOOD)"),
):
    """
    Retrieve list of emergency incidents with optional status, severity, or type filters.
    """
    return incident_service.list_incidents(status=status, severity=severity, incident_type=incident_type)


@router.get("/incidents/{incident_id}", summary="Get Incident Details")
async def get_incident(incident_id: str):
    """
    Retrieve single emergency incident by ID or incident_code.
    """
    item = incident_service.get_incident(incident_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident '{incident_id}' not found.")
    return item


@router.patch("/incidents/{incident_id}", summary="Update Incident")
async def update_incident(incident_id: str, payload: IncidentUpdate):
    """
    Update incident fields (e.g. status, severity, location, assigned_unit_id).
    """
    item = incident_service.update_incident(incident_id, payload)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident '{incident_id}' not found.")
    return item


@router.delete("/incidents/{incident_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Incident")
async def delete_incident(incident_id: str):
    """
    Delete emergency incident by ID or code.
    """
    success = incident_service.delete_incident(incident_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident '{incident_id}' not found.")
    return None


@router.post("/incidents/{incident_id}/resolve", summary="Resolve Emergency Incident")
async def resolve_incident(incident_id: str):
    """
    Mark emergency incident as RESOLVED and record timestamp.
    """
    item = incident_service.resolve_incident(incident_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident '{incident_id}' not found.")
    return item


@router.post("/incidents/{incident_id}/analyze", summary="Analyze Incident AI Priority & Intelligence")
@router.get("/incidents/{incident_id}/intelligence", summary="Get Incident AI Intelligence")
async def analyze_incident(incident_id: str):
    """
    Analyze emergency incident using deterministic AI intelligence engine.
    Calculates priority score (0-100), priority classification, risk level, response urgency,
    recommended unit resources, factor breakdown, and human-readable explanation.
    """
    try:
        result = incident_intelligence_service.analyze_incident(incident_id)
        return result
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"AI analysis failed: {str(e)}")
