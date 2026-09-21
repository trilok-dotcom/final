from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Body
from pydantic import BaseModel

from app.services.command_center_service import command_center_service
from app.utils.logging import get_logger

logger = get_logger("app.api.routes.command_center")

router = APIRouter()


class AcknowledgeAlertRequest(BaseModel):
    operator_id: Optional[str] = "DISPATCH_OPERATOR"


@router.get("/command-center/overview")
def get_command_center_overview():
    """Retrieve unified multi-incident Command Center aggregated dashboard data."""
    try:
        overview = command_center_service.get_overview()
        return overview
    except Exception as e:
        logger.error(f"Error fetching command center overview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load Command Center overview: {str(e)}",
        )


@router.post("/command-center/alerts/{alert_id}/acknowledge")
def acknowledge_command_center_alert(
    alert_id: str,
    payload: Optional[AcknowledgeAlertRequest] = None,
):
    """Acknowledge a Command Center alert."""
    try:
        operator_id = payload.operator_id if payload and payload.operator_id else "DISPATCH_OPERATOR"
        res = command_center_service.acknowledge_alert(alert_id, operator_id=operator_id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error acknowledging alert '{alert_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to acknowledge alert: {str(e)}",
        )
