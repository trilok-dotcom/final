import sys
import time
from pathlib import Path
from typing import Union, Optional, Dict, Any
import numpy as np
import torch
from PIL import Image

AI_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = AI_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ai.inference.road_detector import RoadDetector
from ai.inference.preprocessing import preprocess_image
from ai.inference.postprocessing import (
    postprocess_mask,
    create_road_overlay,
    extract_road_network,
    DEFAULT_THRESHOLD,
)


class RoadPredictor:
    """Production inference interface for RESQROUTE Road Segmentation.

    Loads the PyTorch U-Net ResNet-34 model once at initialization,
    processes satellite images through preprocessing, neural net forward pass,
    post-processing mask binarization, overlay creation, and road network graph extraction.
    """

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        default_threshold: float = DEFAULT_THRESHOLD,
        device: Optional[torch.device] = None,
    ) -> None:
        """Initialize RoadPredictor and load U-Net ResNet-34 model once.

        Args:
            model_path (Optional[Union[str, Path]]): Path to model checkpoint file (.pth).
            default_threshold (float): Default decision threshold for road mask binarization. Must default to 0.25.
            device (Optional[torch.device]): Target compute device (CPU or CUDA).
        """
        self.default_threshold = default_threshold
        # Initialize detector which loads model checkpoint once
        self.detector = RoadDetector(model_path=model_path, device=device)

    @property
    def device(self) -> torch.device:
        """Active computing device ('cuda' or 'cpu')."""
        return self.detector.device

    def predict(
        self,
        image_input: Union[str, Path, np.ndarray, Image.Image],
        threshold: Optional[float] = None,
        min_component_size: int = 50,
        extract_network: bool = True,
        overlay_color: tuple = (0, 255, 255),
    ) -> Dict[str, Any]:
        """Run complete AI road detection pipeline on an input satellite image.

        Args:
            image_input (Union[str, Path, np.ndarray, Image.Image]): Input image.
            threshold (Optional[float]): Custom threshold (overrides default_threshold=0.25).
            min_component_size (int): Minimum pixel component size for mask cleanup.
            extract_network (bool): Whether to build NetworkX road graph representation.
            overlay_color (tuple): RGB color for road mask overlay visualization.

        Returns:
            Dict[str, Any]:
                - probability_map: np.ndarray [512, 512] float32 in range [0, 1]
                - mask: np.ndarray [512, 512] uint8 binary mask (0 or 255)
                - overlay: np.ndarray [512, 512, 3] uint8 RGB image with road overlay
                - road_network: dict containing graph, nodes, edges, and skeleton
                - metadata: dict containing execution stats, device info, road %
        """
        thresh = threshold if threshold is not None else self.default_threshold
        start_time = time.perf_counter()

        # 1. Preprocessing (Resize to 512x512, Normalize ImageNet, Format [1, 3, 512, 512])
        input_tensor, original_rgb = preprocess_image(image_input)

        # 2. Prediction (Torch eval, no_grad, sigmoid probability map [512, 512])
        prob_map = self.detector.predict_probability(input_tensor)

        # 3. Post-processing (Threshold >= 0.25, Morphological Cleanup)
        binary_mask = postprocess_mask(
            prob_map,
            threshold=thresh,
            min_component_size=min_component_size,
        )

        # 4. Road Overlay Image Creation
        overlay_image = create_road_overlay(
            original_rgb,
            binary_mask,
            alpha=0.45,
            color=overlay_color,
        )

        # 5. Road Extraction (Skeletonization & Graph Construction)
        if extract_network:
            road_network = extract_road_network(binary_mask, prob_map=prob_map)
        else:
            road_network = {"graph": None, "nodes": [], "edges": [], "skeleton": None}

        inference_time_ms = (time.perf_counter() - start_time) * 1000.0
        road_pixel_pct = float((np.count_nonzero(binary_mask) / binary_mask.size) * 100.0)

        metadata = {
            "device": str(self.device),
            "input_shape": list(input_tensor.shape),
            "output_shape": list(prob_map.shape),
            "threshold_used": thresh,
            "inference_time_ms": round(inference_time_ms, 2),
            "road_pixel_percentage": round(road_pixel_pct, 2),
        }

        return {
            "probability_map": prob_map,
            "mask": binary_mask,
            "overlay": overlay_image,
            "road_network": road_network,
            "metadata": metadata,
        }
