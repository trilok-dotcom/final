import uuid
import time
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
import cv2
import numpy as np
from fastapi import APIRouter, File, UploadFile, HTTPException, status
from pydantic import BaseModel, Field

from ai.config import AI_DIR
from app.services.ai_service import get_road_predictor
from app.utils.logging import get_logger

logger = get_logger("api.ai_detect")
router = APIRouter()

# Output directory for endpoint generated static images
DETECT_ROADS_OUTPUT_DIR = AI_DIR / "outputs" / "detect_roads"
DETECT_ROADS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


class GraphNodeModel(BaseModel):
    id: int
    x: float
    y: float
    pos: List[float]


class GraphEdgeModel(BaseModel):
    source: int
    target: int
    weight: float
    length: float
    confidence: float
    points: List[List[float]]


class RoadGraphDataModel(BaseModel):
    nodes: List[GraphNodeModel]
    edges: List[GraphEdgeModel]


class RoadDetectionResponse(BaseModel):
    success: bool = True
    inference_time_ms: float = Field(..., description="Neural network inference execution time in milliseconds")
    threshold: float = Field(0.25, description="Binarization decision threshold used (default 0.25)")
    detected_road_pixel_percentage: float = Field(..., description="Percentage of image pixels classified as road")
    graph_nodes: int = Field(..., description="Count of extracted road network graph nodes")
    graph_edges: int = Field(..., description="Count of extracted road network graph edges")
    image_dimensions: List[int] = Field(default_factory=lambda: [512, 512], description="Image height and width [H, W]")
    prediction_url: str = Field(..., description="Static URL to generated probability map image")
    mask_url: str = Field(..., description="Static URL to generated binary road mask image")
    overlay_url: str = Field(..., description="Static URL to generated satellite + road mask overlay image")
    road_graph: RoadGraphDataModel = Field(..., description="Extracted topological road network graph nodes and edges")


@router.post(
    "/detect-roads",
    response_model=RoadDetectionResponse,
    summary="RESQROUTE AI Road Detection Pipeline",
    description="Accepts satellite image upload, runs U-Net ResNet-34 road segmentation, post-processes binary mask with threshold=0.25, generates overlay image, and extracts road graph nodes and edges.",
)
async def detect_roads(file: UploadFile = File(...)):
    """Run production AI inference pipeline on uploaded satellite image."""
    # 1. Validate file upload
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid image file uploaded. Please select a satellite image.",
        )

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{file_ext}'. Allowed formats: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}",
        )

    # 2. Save temporary uploaded file
    req_id = f"req_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
    temp_upload_path = DETECT_ROADS_OUTPUT_DIR / f"{req_id}_upload{file_ext}"

    try:
        with open(temp_upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save upload file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded satellite image on server.",
        )

    # 3. Retrieve singleton predictor instance (model loaded once)
    try:
        predictor = get_road_predictor()
    except FileNotFoundError as e:
        logger.error(f"Missing model checkpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI model checkpoint file missing on server.",
        )
    except Exception as e:
        logger.error(f"Model initialization error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize AI model engine: {str(e)}",
        )

    # 4. Perform AI Road Segmentation Inference
    try:
        res = predictor.predict(temp_upload_path, threshold=0.25, extract_network=True)
    except ValueError as e:
        logger.warning(f"Invalid image content: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Corrupted or invalid satellite image: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Inference failure: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI road detection inference failed: {str(e)}",
        )
    finally:
        # Clean up temporary uploaded input image
        if temp_upload_path.exists():
            try:
                temp_upload_path.unlink()
            except Exception:
                pass

    # 5. Save output artifacts (prediction map, mask, overlay)
    prob_map = res["probability_map"]
    mask = res["mask"]
    overlay = res["overlay"]
    network = res["road_network"]
    meta = res["metadata"]

    prob_path = DETECT_ROADS_OUTPUT_DIR / f"{req_id}_prediction.png"
    mask_path = DETECT_ROADS_OUTPUT_DIR / f"{req_id}_mask.png"
    overlay_path = DETECT_ROADS_OUTPUT_DIR / f"{req_id}_overlay.png"

    # Save images
    prob_uint8 = (prob_map * 255.0).clip(0, 255).astype(np.uint8)
    cv2.imwrite(str(prob_path), prob_uint8)
    cv2.imwrite(str(mask_path), mask)

    overlay_bgr = cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(overlay_path), overlay_bgr)

    # Server-side existence check
    for p in [prob_path, mask_path, overlay_path]:
        if not p.exists():
            logger.error(f"Generated output file missing on server: {p}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Generated output artifact missing on server: {p.name}"
            )

    # Relative static URLs
    pred_url = f"/outputs/detect_roads/{prob_path.name}"
    mask_url = f"/outputs/detect_roads/{mask_path.name}"
    overlay_url = f"/outputs/detect_roads/{overlay_path.name}"

    nodes_data = [
        GraphNodeModel(
            id=n["id"],
            x=n["x"],
            y=n["y"],
            pos=[float(n["pos"][0]), float(n["pos"][1])],
        )
        for n in network["nodes"]
    ]

    edges_data = [
        GraphEdgeModel(
            source=e["source"],
            target=e["target"],
            weight=e["weight"],
            length=e["length"],
            confidence=e["confidence"],
            points=[[float(pt[0]), float(pt[1])] for pt in e.get("points", [])],
        )
        for e in network["edges"]
    ]

    return RoadDetectionResponse(
        success=True,
        inference_time_ms=meta["inference_time_ms"],
        threshold=meta["threshold_used"],
        detected_road_pixel_percentage=meta["road_pixel_percentage"],
        graph_nodes=len(nodes_data),
        graph_edges=len(edges_data),
        image_dimensions=[512, 512],
        prediction_url=pred_url,
        mask_url=mask_url,
        overlay_url=overlay_url,
        road_graph=RoadGraphDataModel(nodes=nodes_data, edges=edges_data),
    )
