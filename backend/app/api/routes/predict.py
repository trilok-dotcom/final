import shutil
import time
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException, status
from pydantic import BaseModel, Field

from ai.predict import predictor
from app.utils.logging import get_logger

logger = get_logger("api.predict")
router = APIRouter()


class PredictResponse(BaseModel):
    success: bool = True
    confidence: float = Field(..., description="Mean prediction confidence on detected road pixels (0-1)")
    road_percentage: float = Field(..., description="Road area coverage percentage (0-100)")
    inference_time_ms: float = Field(..., description="Inference execution time in milliseconds")
    mask_url: str = Field(..., description="URL path to generated binary road mask image")
    overlay_url: str = Field(..., description="URL path to generated road overlay image")
    heatmap_url: str = Field(..., description="URL path to generated probability heatmap image")


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


@router.post(
    "/predict",
    response_model=PredictResponse,
    summary="U-Net Satellite Road Segmentation Inference",
    description="Accepts a satellite image upload and runs the trained U-Net ResNet-34 model to detect road networks.",
)
async def predict_satellite_image(file: UploadFile = File(...)):
    # 1. Validate uploaded file and filename
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a valid file with a filename."
        )

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file_ext}'. Allowed image extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # 2. Ensure model is loaded or attempt loading
    if not predictor.is_loaded:
        try:
            predictor.load_model()
        except Exception as e:
            logger.error(f"Failed to load AI model: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI model loading failure: {str(e)}"
            )

    # 3. Save temporary server-side uploaded image
    upload_dir = predictor.output_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_file_path = upload_dir / f"upload_{int(time.time() * 1000)}{file_ext}"

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process uploaded file on server."
        )

    # 4. Perform AI Inference
    try:
        result = predictor.predict(image_path=temp_file_path)
    except Exception as e:
        logger.error(f"AI Inference error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI model inference error: {str(e)}"
        )

    # 5. Extract URLs for generated static output images
    mask_path = result["output_image_paths"]["prediction_mask.png"]
    overlay_path = result["output_image_paths"]["prediction_overlay.png"]
    heatmap_path = result["output_image_paths"]["prediction_heatmap.png"]

    # Server-side existence check
    for p in [mask_path, overlay_path, heatmap_path]:
        if not Path(p).exists():
            logger.error(f"Generated output file missing on server: {p}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Generated output artifact missing on server: {Path(p).name}"
            )

    mask_name = Path(mask_path).name
    overlay_name = Path(overlay_path).name
    heatmap_name = Path(heatmap_path).name

    return PredictResponse(
        success=True,
        confidence=round(float(result["prediction_confidence"]), 4),
        road_percentage=round(float(result["road_coverage_percentage"]), 2),
        inference_time_ms=round(float(result["inference_time_ms"]), 2),
        mask_url=f"/outputs/{mask_name}",
        overlay_url=f"/outputs/{overlay_name}",
        heatmap_url=f"/outputs/{heatmap_name}",
    )
