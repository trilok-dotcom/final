from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Body, status
from pydantic import BaseModel

from app.services.road_condition_service import road_condition_service
from app.utils.logging import get_logger

logger = get_logger("app.api.routes.road_condition")

router = APIRouter()


class AnalyzeRequest(BaseModel):
    pre_image_name: Optional[str] = None
    post_image_name: Optional[str] = None
    demo_scenario: Optional[str] = "SECTOR_4_FLOOD"


@router.post("/road-condition/analyze", status_code=status.HTTP_200_OK)
def analyze_road_condition(payload: Optional[AnalyzeRequest] = Body(None)) -> Dict[str, Any]:
    """Analyze post-disaster road conditions comparing baseline and post-disaster satellite imagery."""
    try:
        pre_img = payload.pre_image_name if payload else None
        post_img = payload.post_image_name if payload else None
        demo = payload.demo_scenario if payload else "SECTOR_4_FLOOD"

        result = road_condition_service.analyze_road_condition(
            pre_image=pre_img,
            post_image=post_img,
            demo_scenario=demo,
        )
        return result
    except Exception as e:
        logger.error(f"Failed to analyze road condition: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Post-disaster road condition analysis failed: {str(e)}",
        )


@router.get("/road-condition/active", status_code=status.HTTP_200_OK)
def get_active_road_condition() -> Dict[str, Any]:
    """Get the currently active post-disaster road condition assessment applied to emergency routing."""
    active = road_condition_service.get_active_assessment()
    if not active:
        return {
            "active": False,
            "message": "No active post-disaster road assessment. Routing is operating on baseline graph.",
        }
    return {
        "active": True,
        "assessment": active,
    }


@router.get("/road-condition/{assessment_id}", status_code=status.HTTP_200_OK)
def get_road_condition_assessment(assessment_id: str) -> Dict[str, Any]:
    """Get specific post-disaster road condition assessment details."""
    res = road_condition_service.get_assessment(assessment_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Road condition assessment '{assessment_id}' not found.",
        )
    return res


@router.post("/road-condition/{assessment_id}/apply", status_code=status.HTTP_200_OK)
def apply_road_condition_assessment(assessment_id: str) -> Dict[str, Any]:
    """Activate specified post-disaster road condition assessment for system emergency routing."""
    try:
        res = road_condition_service.apply_assessment(assessment_id)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to apply road assessment '{assessment_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply road assessment: {str(e)}",
        )


@router.post("/road-condition/reset", status_code=status.HTTP_200_OK)
def reset_road_condition_assessment() -> Dict[str, Any]:
    """Reset system routing back to baseline (deactivate active post-disaster assessment)."""
    return road_condition_service.reset_active_assessment()
