import shutil
import time
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException, status
from pydantic import BaseModel, Field

from ai.config import AI_DIR
from ai.predict import predictor
from app.services.road_network_service import road_network_service
from app.utils.logging import get_logger

logger = get_logger("api.road_network")
router = APIRouter()


class RoadNetworkRequest(BaseModel):
    mask_path: str = Field(..., description="Path or relative URL to existing U-Net prediction mask image")


class RoadNetworkResponse(BaseModel):
    success: bool = True
    road_pixels: int = Field(..., description="Total count of detected road mask pixels")
    road_coverage_percentage: float = Field(..., description="Road area coverage percentage")
    graph_nodes: int = Field(..., description="Total count of graph nodes extracted")
    graph_edges: int = Field(..., description="Total count of graph edges extracted")
    connected_components: int = Field(..., description="Count of disconnected road network components")
    largest_component_nodes: int = Field(..., description="Node count of largest connected road network component")
    skeleton_url: str = Field(..., description="Static URL to generated road skeleton image")
    overlay_url: str = Field(..., description="Static URL to generated road network overlay image")
    comparison_url: str = Field(..., description="Static URL to generated 4-panel comparison grid image")
    geojson_url: str = Field(..., description="Static URL to generated GeoJSON network file")


class AnalyzeSatelliteResponse(BaseModel):
    success: bool = True
    prediction: dict = Field(..., description="U-Net prediction confidence, coverage, and image URLs")
    road_network: dict = Field(..., description="Extracted graph stats, GeoJSON, skeleton & overlay URLs")


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


@router.post(
    "/road-network",
    response_model=RoadNetworkResponse,
    summary="Extract Road Network Graph from Prediction Mask",
    description="Processes binary road prediction mask to skeletonize road centerlines, build NetworkX graph, and export GeoJSON."
)
async def extract_road_network_from_mask(request: RoadNetworkRequest):
    # Resolve mask path
    raw_path = request.mask_path.lstrip("/").replace("outputs/", "")
    mask_file = AI_DIR / "outputs" / raw_path

    if not mask_file.exists():
        # Fallback to direct path
        mask_file = Path(request.mask_path)
        if not mask_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prediction mask file not found at '{request.mask_path}'"
            )

    try:
        res = road_network_service.process_road_network(
            mask_path=mask_file,
            output_dir=AI_DIR / "outputs",
        )
    except Exception as e:
        logger.error(f"Road network extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Road network extraction failed: {str(e)}"
        )

    return RoadNetworkResponse(
        success=True,
        road_pixels=res["road_pixels"],
        road_coverage_percentage=res["road_coverage_percentage"],
        graph_nodes=res["graph_nodes"],
        graph_edges=res["graph_edges"],
        connected_components=res["connected_components"],
        largest_component_nodes=res["largest_component_nodes"],
        skeleton_url="/outputs/road_skeleton.png",
        overlay_url="/outputs/road_network_overlay.png",
        comparison_url="/outputs/prediction_comparison.png",
        geojson_url="/outputs/road_network.geojson",
    )


@router.post(
    "/analyze-satellite",
    response_model=AnalyzeSatelliteResponse,
    summary="Combined Satellite Image Analysis Pipeline",
    description="Full automated end-to-end pipeline: Satellite Image -> U-Net Segmentation -> Road Network Extraction -> Graph & GeoJSON Output."
)
async def analyze_satellite_image(file: UploadFile = File(...)):
    # 1. Validate Upload File
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a valid image file with a filename."
        )

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{file_ext}'. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # 2. Save uploaded satellite image temporarily
    upload_dir = predictor.output_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_sat_path = upload_dir / f"sat_{int(time.time() * 1000)}{file_ext}"

    try:
        with open(temp_sat_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save uploaded satellite image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded satellite image on server."
        )

    # 3. U-Net AI Road Segmentation Inference
    try:
        pred_res = predictor.predict(image_path=temp_sat_path)
    except Exception as e:
        logger.error(f"U-Net inference error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"U-Net inference error: {str(e)}"
        )

    mask_path = Path(pred_res["mask_output_path"])

    # 4. Extract Real Road Network & Build Graph
    try:
        network_res = road_network_service.process_road_network(
            mask_path=mask_path,
            sat_path=temp_sat_path,
            output_dir=predictor.output_dir,
        )
    except Exception as e:
        logger.error(f"Road network extraction error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Road network extraction error: {str(e)}"
        )

    mask_name = Path(pred_res["output_image_paths"]["prediction_mask.png"]).name
    pred_overlay_name = Path(pred_res["output_image_paths"]["prediction_overlay.png"]).name
    heatmap_name = Path(pred_res["output_image_paths"]["prediction_heatmap.png"]).name

    return AnalyzeSatelliteResponse(
        success=True,
        prediction={
            "confidence": round(float(pred_res["prediction_confidence"]), 4),
            "road_percentage": round(float(pred_res["road_coverage_percentage"]), 2),
            "mask_url": f"/outputs/{mask_name}",
            "overlay_url": f"/outputs/{pred_overlay_name}",
            "heatmap_url": f"/outputs/{heatmap_name}",
        },
        road_network={
            "road_pixels": network_res["road_pixels"],
            "graph_nodes": network_res["graph_nodes"],
            "graph_edges": network_res["graph_edges"],
            "coverage_percentage": network_res["road_coverage_percentage"],
            "connected_components": network_res["connected_components"],
            "largest_component_nodes": network_res["largest_component_nodes"],
            "skeleton_url": "/outputs/road_skeleton.png",
            "overlay_url": "/outputs/road_network_overlay.png",
            "comparison_url": "/outputs/prediction_comparison.png",
            "geojson_url": "/outputs/road_network.geojson",
        },
    )
