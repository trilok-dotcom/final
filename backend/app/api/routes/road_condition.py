import uuid
from typing import Dict, Any, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Body, File, UploadFile, Form, Request, status
from pydantic import BaseModel

from app.services.road_condition_service import road_condition_service, BACKEND_DIR, AI_DIR
from app.utils.logging import get_logger

logger = get_logger("app.api.routes.road_condition")

router = APIRouter()


class AnalyzeRequest(BaseModel):
    pre_image_name: Optional[str] = None
    post_image_name: Optional[str] = None
    demo_scenario: Optional[str] = "SECTOR_4_FLOOD"


@router.post("/road-condition/analyze", status_code=status.HTTP_200_OK)
async def analyze_road_condition(
    request: Request,
    before_image: Optional[UploadFile] = File(None),
    after_image: Optional[UploadFile] = File(None),
    demo_scenario: Optional[str] = Form(None),
) -> Dict[str, Any]:
    """Analyze post-disaster road conditions comparing baseline and post-disaster satellite imagery.
    
    Supports both multipart/form-data file uploads (before_image, after_image) and JSON payloads.
    """
    try:
        pre_file_path: Optional[Path] = None
        post_file_path: Optional[Path] = None
        scenario: Optional[str] = demo_scenario or "SECTOR_4_FLOOD"

        content_type = request.headers.get("content-type", "")

        if "multipart/form-data" in content_type:
            uploads_dir = BACKEND_DIR / "outputs" / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            session_id = uuid.uuid4().hex[:8]

            if before_image and before_image.filename:
                before_ext = Path(before_image.filename).suffix or ".png"
                pre_file_path = uploads_dir / f"before_{session_id}{before_ext}"
                content = await before_image.read()
                with open(pre_file_path, "wb") as buffer:
                    buffer.write(content)

            if after_image and after_image.filename:
                after_ext = Path(after_image.filename).suffix or ".png"
                post_file_path = uploads_dir / f"after_{session_id}{after_ext}"
                content = await after_image.read()
                with open(post_file_path, "wb") as buffer:
                    buffer.write(content)
        else:
            # Parse JSON body for backward compatibility
            try:
                body_json = await request.json()
                if isinstance(body_json, dict):
                    pre_name = body_json.get("pre_image_name")
                    post_name = body_json.get("post_image_name")
                    scenario = body_json.get("demo_scenario", "SECTOR_4_FLOOD")
                    if pre_name:
                        pre_file_path = AI_DIR / "datasets" / "processed" / "images" / pre_name
                    if post_name:
                        post_file_path = AI_DIR / "datasets" / "processed" / "images" / post_name
            except Exception:
                pass

        result = road_condition_service.analyze_road_condition(
            pre_image=pre_file_path,
            post_image=post_file_path,
            demo_scenario=scenario,
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
