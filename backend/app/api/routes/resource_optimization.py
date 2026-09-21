from fastapi import APIRouter, HTTPException, status
from app.services.resource_optimizer_service import resource_optimizer_service

router = APIRouter()


@router.post(
    "/incidents/{incident_id}/optimize-resources",
    summary="Optimize Multi-Unit Rescue Resources for Emergency Incident",
)
async def optimize_incident_resources(incident_id: str):
    """
    Calculate optimal multi-unit rescue plan consuming Stage 8A recommendations.
    Evaluates candidates using in-process U-Net Dijkstra AI routes, ranks candidates, and reserves units.
    """
    try:
        result = resource_optimizer_service.optimize_incident_resources(incident_id)
        return result
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Resource optimization failed: {str(e)}")


@router.post(
    "/incidents/{incident_id}/dispatch-optimized",
    summary="Dispatch Operator-Confirmed Multi-Unit Optimized Plan",
)
async def dispatch_optimized_plan(incident_id: str):
    """
    Confirm operator action and dispatch all reserved units for incident.
    Creates individual Stage 7B dispatch records with AI routes and updates unit states.
    """
    try:
        result = resource_optimizer_service.dispatch_optimized_plan(incident_id)
        return result
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        if "CONFLICT" in msg or "no longer available" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Optimized dispatch failed: {str(e)}")
