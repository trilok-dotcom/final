import sys
from pathlib import Path
from typing import Optional
from app.utils.logging import get_logger

AI_DIR = Path(__file__).resolve().parent.parent.parent / "ai"
if str(AI_DIR.parent) not in sys.path:
    sys.path.insert(0, str(AI_DIR.parent))

from ai.inference import RoadPredictor, get_inference_device

logger = get_logger("app.services.ai_service")

# Global singleton instance of RoadPredictor
_predictor_instance: Optional[RoadPredictor] = None


def get_road_predictor() -> RoadPredictor:
    """Get or lazily initialize the singleton RoadPredictor instance.

    Ensures the U-Net + ResNet-34 model is loaded ONCE in memory and reused
    across all API requests without reloading weights per request.
    """
    global _predictor_instance
    if _predictor_instance is None:
        logger.info("Initializing RESQROUTE RoadPredictor (loading U-Net model)...")
        _predictor_instance = RoadPredictor(default_threshold=0.25)
        logger.info(f"RoadPredictor initialized on device: '{_predictor_instance.device}'")
    return _predictor_instance


def init_road_predictor() -> None:
    """Warm up/initialize the RoadPredictor singleton during application startup."""
    get_road_predictor()
