import sys
import time
import argparse
from pathlib import Path
from typing import Dict, Any, Union, Optional
import cv2
import numpy as np
import torch

# Ensure backend parent directory is in sys.path for standalone module execution
AI_DIR = Path(__file__).resolve().parent
BACKEND_DIR = AI_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ai import config
from ai.dataset import get_default_transforms
from ai.model import RoadSegmentationModel, get_default_device


def predict(
    image_path: Union[str, Path],
    weights_path: Optional[Union[str, Path]] = None,
    output_dir: Optional[Union[str, Path]] = None,
    threshold: float = 0.5,
    device: Optional[torch.device] = None,
) -> Dict[str, Any]:
    """Run U-Net road segmentation inference on a single satellite image.

    Args:
        image_path (Union[str, Path]): Path to input satellite image file.
        weights_path (Optional[Union[str, Path]]): Model weights path. Defaults to 'weights/best_model.pth'.
        output_dir (Optional[Union[str, Path]]): Directory to save generated output images. Defaults to 'outputs/'.
        threshold (float): Probability threshold for binarizing road mask. Default 0.5.
        device (Optional[torch.device]): Target hardware device (CPU or CUDA). Auto-detected if None.

    Returns:
        Dict[str, Any]: Dictionary containing prediction confidence, inference time, road coverage %,
                        background %, and saved output image file paths.
    """
    img_file = Path(image_path)
    if not img_file.exists():
        raise FileNotFoundError(f"Input satellite image not found at '{img_file}'")

    # 1. Automatically load weights/best_model.pth (fallback to weights/last_model.pth if best_model.pth not yet created)
    if weights_path is None:
        target_weights = AI_DIR / "weights" / "best_model.pth"
        if not target_weights.exists():
            fallback_weights = AI_DIR / "weights" / "last_model.pth"
            if fallback_weights.exists():
                target_weights = fallback_weights
            else:
                raise FileNotFoundError(
                    f"No model checkpoint found at '{target_weights}' or '{fallback_weights}'. "
                    "Please run train.py first to generate model weights."
                )
    else:
        target_weights = Path(weights_path)
        if not target_weights.exists():
            raise FileNotFoundError(f"Specified model weights file not found at '{target_weights}'")

    # 2. Configure output directory (outputs/)
    out_dir = Path(output_dir) if output_dir else (AI_DIR / "outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 3. Detect and set device (CPU / CUDA support automatically)
    target_device = device or get_default_device()

    # 4. Load PyTorch U-Net Model
    model = RoadSegmentationModel(device=target_device)
    model.load_model(target_weights, device=target_device)
    model.eval()

    # 5. Load input satellite image and resize to 512x512
    img_bgr = cv2.imread(str(img_file), cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError(f"Failed to read image at '{img_file}'. Ensure it is a valid image file.")

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    img_resized_bgr = cv2.resize(img_bgr, (config.IMAGE_WIDTH, config.IMAGE_HEIGHT))
    img_resized_rgb = cv2.resize(img_rgb, (config.IMAGE_WIDTH, config.IMAGE_HEIGHT))

    # Normalize using the exact same preprocessing used during model training
    transform = get_default_transforms(
        split="valid",
        image_height=config.IMAGE_HEIGHT,
        image_width=config.IMAGE_WIDTH,
    )
    transformed = transform(image=img_resized_rgb)
    input_tensor = transformed["image"].unsqueeze(0).to(target_device)  # Shape: (1, 3, 512, 512)

    # 6. Perform Inference & Time Execution
    start_time = time.perf_counter()
    with torch.no_grad():
        logits = model(input_tensor)
        # Apply Sigmoid Activation
        probabilities = torch.sigmoid(logits).squeeze().cpu().numpy()  # Shape: (512, 512)
    inference_time_sec = time.perf_counter() - start_time
    inference_time_ms = inference_time_sec * 1000.0

    # 7. Apply Decision Threshold (0.5)
    binary_mask_bool = probabilities > threshold
    binary_mask_uint8 = (binary_mask_bool.astype(np.uint8)) * 255

    # 8. Compute Statistics
    total_pixels = binary_mask_bool.size
    road_pixels = int(np.sum(binary_mask_bool))
    background_pixels = total_pixels - road_pixels

    road_coverage_pct = (road_pixels / total_pixels) * 100.0
    background_pct = (background_pixels / total_pixels) * 100.0

    if road_pixels > 0:
        prediction_confidence = float(np.mean(probabilities[binary_mask_bool]))
    else:
        prediction_confidence = float(np.max(probabilities))

    # 9. Generate and Save Outputs inside outputs/
    # A. Binary Mask (outputs/prediction_mask.png)
    mask_output_path = out_dir / "prediction_mask.png"
    cv2.imwrite(str(mask_output_path), binary_mask_uint8)

    # B. Overlay Image (outputs/prediction_overlay.png)
    overlay_bgr = img_resized_bgr.copy()
    green_mask = np.zeros_like(img_resized_bgr)
    green_mask[binary_mask_bool] = [0, 255, 0]  # BGR Green

    alpha = 0.45
    blended = cv2.addWeighted(img_resized_bgr, 1.0 - alpha, green_mask, alpha, 0)
    overlay_bgr[binary_mask_bool] = blended[binary_mask_bool]
    overlay_output_path = out_dir / "prediction_overlay.png"
    cv2.imwrite(str(overlay_output_path), overlay_bgr)

    # C. Heatmap (outputs/prediction_heatmap.png)
    prob_uint8 = (probabilities * 255.0).astype(np.uint8)
    heatmap_bgr = cv2.applyColorMap(prob_uint8, cv2.COLORMAP_JET)
    heatmap_output_path = out_dir / "prediction_heatmap.png"
    cv2.imwrite(str(heatmap_output_path), heatmap_bgr)

    # 10. Print Inference Statistics to Console
    print("==================================================")
    print("      RESQROUTE AI - INFERENCE STATISTICS        ")
    print("==================================================")
    print(f"Input Image          : {img_file.name}")
    print(f"Loaded Weights       : {target_weights.name}")
    print(f"Target Device        : {target_device}")
    print(f"Inference Time       : {inference_time_ms:.2f} ms ({inference_time_sec:.4f} s)")
    print(f"Prediction Confidence: {prediction_confidence * 100.0:.2f}% ({prediction_confidence:.4f})")
    print(f"Road Coverage        : {road_coverage_pct:.2f}% ({road_pixels:,} pixels)")
    print(f"Background Coverage  : {background_pct:.2f}% ({background_pixels:,} pixels)")
    print("\nSaved Visualizations in outputs/:")
    print(f"  - Binary Mask      : {mask_output_path}")
    print(f"  - Overlay Image    : {overlay_output_path}")
    print(f"  - Probability Map  : {heatmap_output_path}")
    print("==================================================\n")

    # 11. Return Results Dictionary
    return {
        "confidence": prediction_confidence,
        "prediction_confidence": prediction_confidence,
        "safe_roads_pct": road_coverage_pct,
        "road_coverage_percentage": road_coverage_pct,
        "damaged_roads_pct": 0.0,
        "blocked_roads_pct": 0.0,
        "background_percentage": background_pct,
        "mask_output_path": str(mask_output_path),
        "inference_time_ms": inference_time_ms,
        "inference_time_sec": inference_time_sec,
        "output_image_paths": {
            "prediction_mask.png": str(mask_output_path),
            "prediction_overlay.png": str(overlay_output_path),
            "prediction_heatmap.png": str(heatmap_output_path),
        },
    }


class UNetPredictor:
    """Predictor service wrapper for PyTorch U-Net inference."""

    def __init__(self, model_path: Optional[Union[str, Path]] = None) -> None:
        self.model_path = Path(model_path) if model_path else (AI_DIR / "weights" / "best_model.pth")
        self.model: Optional[RoadSegmentationModel] = None
        self.device: Optional[torch.device] = None
        self.output_dir: Path = AI_DIR / "outputs"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_loaded(self) -> bool:
        """Check if model state dict is loaded in memory or weights checkpoint file exists."""
        return self.model is not None or self.model_path.exists() or (AI_DIR / "weights" / "last_model.pth").exists()

    def load_model(self, force_reload: bool = False) -> RoadSegmentationModel:
        """Load model weights into memory with startup logging."""
        if self.model is not None and not force_reload:
            return self.model

        target_weights = self.model_path
        if not target_weights.exists():
            fallback_weights = AI_DIR / "weights" / "last_model.pth"
            if fallback_weights.exists():
                target_weights = fallback_weights
            else:
                raise FileNotFoundError(
                    f"No model checkpoint found at '{target_weights}' or '{fallback_weights}'."
                )

        self.device = get_default_device()
        try:
            from app.utils.logging import get_logger
            logger = get_logger("ai.predict")
        except ImportError:
            import logging
            logger = logging.getLogger("ai.predict")

        logger.info("==================================================")
        logger.info("       RESQROUTE AI MODEL INITIALIZATION          ")
        logger.info("==================================================")
        logger.info(f"AI model loaded   : Initializing state_dict...")
        logger.info(f"Model device      : {self.device}")
        logger.info(f"Model architecture: U-Net (ResNet-34 Encoder, 3 channels in, 1 class out)")
        logger.info(f"Weights path      : {target_weights.resolve()}")

        self.model = RoadSegmentationModel(
            encoder_name="resnet34",
            encoder_weights=None,
            in_channels=3,
            classes=1,
            device=self.device,
        )
        self.model.load_model(target_weights, device=self.device)
        self.model.eval()
        self.model_path = target_weights

        logger.info("AI model loaded   : SUCCESS")
        logger.info("==================================================")
        return self.model

    def predict(
        self,
        image_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """Execute inference using configured model weights."""
        if self.model is None:
            self.load_model()

        target_out_dir = Path(output_dir) if output_dir else self.output_dir
        return predict(
            image_path=image_path,
            weights_path=self.model_path,
            output_dir=target_out_dir,
            threshold=threshold,
            device=self.device,
        )

    async def predict_road_damage(self, image_path: str) -> Dict[str, Any]:
        """Async helper method for road segmentation inference."""
        return self.predict(image_path=image_path)


predictor = UNetPredictor()



def _find_test_image() -> Path:
    """Find an available sample satellite image or generate a test sample image."""
    for split_dir in [config.TRAIN_DIR, config.VALID_DIR, config.TEST_DIR]:
        if split_dir.exists():
            samples = list(split_dir.glob(f"*{config.SAT_SUFFIX}.*"))
            if samples:
                return samples[0]

    sample_dir = config.DATASETS_DIR / "sample"
    sample_dir.mkdir(parents=True, exist_ok=True)
    sample_path = sample_dir / "test_satellite_sat.jpg"

    dummy_sat = np.full((512, 512, 3), (34, 139, 34), dtype=np.uint8)
    cv2.line(dummy_sat, (0, 256), (512, 256), (180, 180, 180), 24)
    cv2.imwrite(str(sample_path), cv2.cvtColor(dummy_sat, cv2.COLOR_RGB2BGR))
    return sample_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run U-Net Satellite Road Segmentation Inference")
    parser.add_argument("--image", type=str, default=None, help="Path to input satellite image")
    parser.add_argument("--weights", type=str, default=None, help="Path to model weights checkpoint (.pth)")
    parser.add_argument("--threshold", type=float, default=0.5, help="Probability threshold (default 0.5)")
    args = parser.parse_args()

    input_image = Path(args.image) if args.image else _find_test_image()

    predict(
        image_path=input_image,
        weights_path=args.weights,
        threshold=args.threshold,
    )
