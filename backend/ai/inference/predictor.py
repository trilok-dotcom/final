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

        Preserves original image dimensions. Uses U-Net ResNet-34 model with
        ImageNet normalization, threshold 0.25, and multi-tile/sliding window
        reconstruction for high-resolution images.

        Args:
            image_input (Union[str, Path, np.ndarray, Image.Image]): Input image.
            threshold (Optional[float]): Custom threshold (overrides default_threshold=0.25).
            min_component_size (int): Minimum pixel component size for mask cleanup.
            extract_network (bool): Whether to build NetworkX road graph representation.
            overlay_color (tuple): RGB color for road mask overlay visualization.

        Returns:
            Dict[str, Any]:
                - probability_map: np.ndarray [H, W] float32 in range [0, 1]
                - mask: np.ndarray [H, W] uint8 binary mask (0 or 255)
                - overlay: np.ndarray [H, W, 3] uint8 RGB image with road overlay
                - road_network: dict containing graph, nodes, edges, and skeleton
                - metadata: dict containing execution stats, device info, road %
        """
        import cv2
        from ai.inference.preprocessing import load_image_raw_rgb, NORM_MEAN, NORM_STD

        thresh = threshold if threshold is not None else self.default_threshold
        start_time = time.perf_counter()

        # 1. Load original RGB image without altering resolution
        original_rgb = load_image_raw_rgb(image_input)
        h_orig, w_orig = original_rgb.shape[:2]

        if h_orig == 512 and w_orig == 512:
            # Standard single forward pass for 512x512 chip
            input_tensor, _ = preprocess_image(original_rgb, target_size=(512, 512))
            prob_map = self.detector.predict_probability(input_tensor)
        else:
            # Arbitrary image size: Tiled sliding-window inference + scaled context ensemble
            prob_accum = np.zeros((h_orig, w_orig), dtype=np.float32)
            weight_accum = np.zeros((h_orig, w_orig), dtype=np.float32)

            tile_size = 512
            stride = 256
            
            # Smooth 2D Hanning window to prevent tile seam artifacts
            window_1d = np.hanning(tile_size)
            window_2d = np.outer(window_1d, window_1d).astype(np.float32) + 1e-5

            y_steps = list(range(0, max(1, h_orig - tile_size + 1), stride))
            if y_steps[-1] + tile_size < h_orig:
                y_steps.append(h_orig - tile_size)
            x_steps = list(range(0, max(1, w_orig - tile_size + 1), stride))
            if x_steps[-1] + tile_size < w_orig:
                x_steps.append(w_orig - tile_size)

            for y in y_steps:
                for x in x_steps:
                    y_end = min(y + tile_size, h_orig)
                    x_end = min(x + tile_size, w_orig)
                    y_start = max(0, y_end - tile_size)
                    x_start = max(0, x_end - tile_size)

                    tile_rgb = original_rgb[y_start:y_end, x_start:x_end]
                    if tile_rgb.shape[:2] != (tile_size, tile_size):
                        tile_rgb = cv2.resize(tile_rgb, (tile_size, tile_size), interpolation=cv2.INTER_LINEAR)

                    # Normalize tile using ImageNet mean/std
                    img_float = tile_rgb.astype(np.float32) / 255.0
                    img_norm = (img_float - NORM_MEAN) / NORM_STD
                    tensor_chw = np.transpose(img_norm, (2, 0, 1))
                    tile_tensor = torch.from_numpy(tensor_chw).unsqueeze(0).float()

                    prob_tile = self.detector.predict_probability(tile_tensor)

                    prob_accum[y_start:y_end, x_start:x_end] += prob_tile * window_2d
                    weight_accum[y_start:y_end, x_start:x_end] += window_2d

            prob_map_tiled = np.divide(prob_accum, np.maximum(weight_accum, 1e-5))

            # Scaled global context pass
            resized_rgb = cv2.resize(original_rgb, (512, 512), interpolation=cv2.INTER_LINEAR)
            img_float = resized_rgb.astype(np.float32) / 255.0
            img_norm = (img_float - NORM_MEAN) / NORM_STD
            tensor_chw = np.transpose(img_norm, (2, 0, 1))
            global_tensor = torch.from_numpy(tensor_chw).unsqueeze(0).float()
            prob_512 = self.detector.predict_probability(global_tensor)
            prob_global = cv2.resize(prob_512, (w_orig, h_orig), interpolation=cv2.INTER_LINEAR)

            # Ensemble: 60% tiled high-res details + 40% global context
            prob_map = 0.60 * prob_map_tiled + 0.40 * prob_global

        # 3. Post-processing (Threshold >= 0.25, Morphological Cleanup)
        binary_mask = postprocess_mask(
            prob_map,
            threshold=thresh,
            min_component_size=min_component_size,
        )

        # 4. Road Overlay Image Creation (at original dimensions)
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
            "input_shape": [1, 3, h_orig, w_orig],
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

