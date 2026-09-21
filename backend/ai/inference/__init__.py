"""RESQROUTE AI Inference Pipeline Package.

Provides high-level inference interface for road segmentation using trained U-Net + ResNet-34.
"""

from ai.inference.road_detector import RoadDetector, get_inference_device
from ai.inference.preprocessing import preprocess_image
from ai.inference.postprocessing import (
    postprocess_mask,
    create_road_overlay,
    extract_road_network,
    DEFAULT_THRESHOLD,
)
from ai.inference.predictor import RoadPredictor

__all__ = [
    "RoadPredictor",
    "RoadDetector",
    "preprocess_image",
    "postprocess_mask",
    "create_road_overlay",
    "extract_road_network",
    "get_inference_device",
    "DEFAULT_THRESHOLD",
]
