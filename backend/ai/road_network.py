import sys
import argparse
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, Union
import cv2
import numpy as np
from skimage.morphology import skeletonize
from PIL import Image

AI_DIR = Path(__file__).resolve().parent
BACKEND_DIR = AI_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ============================================================
# RESQROUTE AI - CONFIGURABLE ROAD MASK CLEANING & SKELETONIZATION
# ============================================================

DEFAULT_SAT_PATH = (
    AI_DIR
    / "datasets"
    / "test"
    / "100703_sat.jpg"
)

DEFAULT_MASK_PATH = (
    AI_DIR
    / "outputs"
    / "prediction_mask.png"
)

DEFAULT_OUTPUT_DIR = (
    AI_DIR
    / "outputs"
    / "road_network"
)

DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Configurable Preprocessing Parameters
ROAD_THRESHOLD = 0.40           # Binarization probability threshold (0-1 range or 0-255 uint8)
MIN_COMPONENT_SIZE = 80         # Remove noise clusters smaller than this pixel area
MORPH_KERNEL_SIZE = 3           # Kernel size for morphological cleanup
MORPH_CLOSE_ITERATIONS = 2      # Fill small holes in roads
MORPH_OPEN_ITERATIONS = 1       # Remove minor isolated pixel spurs


def clean_road_mask(
    mask_input: np.ndarray,
    road_threshold: float = ROAD_THRESHOLD,
    min_component_size: int = MIN_COMPONENT_SIZE,
    kernel_size: int = MORPH_KERNEL_SIZE,
    close_iterations: int = MORPH_CLOSE_ITERATIONS,
    open_iterations: int = MORPH_OPEN_ITERATIONS,
) -> np.ndarray:
    """Preprocess, threshold, and clean AI road prediction mask.

    Args:
        mask_input (np.ndarray): 2D numpy array (grayscale uint8 0-255 or float 0-1).
        road_threshold (float): Binarization threshold.
        min_component_size (int): Minimum component area in pixels.
        kernel_size (int): Morphological structuring element size.
        close_iterations (int): Iterations for MORPH_CLOSE.
        open_iterations (int): Iterations for MORPH_OPEN.

    Returns:
        np.ndarray: Cleaned binary mask (uint8 0 or 255).
    """
    # 1. Binarize mask
    if mask_input.dtype in (np.float32, np.float64):
        binary = (mask_input >= road_threshold).astype(np.uint8) * 255
    else:
        thresh_val = int(road_threshold * 255) if road_threshold <= 1.0 else int(road_threshold)
        binary = np.zeros_like(mask_input, dtype=np.uint8)
        binary[mask_input >= thresh_val] = 255

    # 2. Morphological Closing (bridge narrow gaps along roads)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=close_iterations)

    # 3. Morphological Opening (remove minor background noise)
    opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel, iterations=open_iterations)

    # 4. Connected Component Filtering (remove small isolated noise specs)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(opened, connectivity=8)
    cleaned = np.zeros_like(opened)

    for i in range(1, num_labels):  # Skip background (label 0)
        area = stats[i, cv2.CC_STAT_AREA]
        if area >= min_component_size:
            cleaned[labels == i] = 255

    return cleaned


def extract_road_skeleton(cleaned_mask: np.ndarray) -> np.ndarray:
    """Skeletonize cleaned 2D road mask down to 1-pixel thin centerlines.

    Args:
        cleaned_mask (np.ndarray): Binary uint8 road mask (0 or 255).

    Returns:
        np.ndarray: Binarized uint8 skeleton image (0 or 255).
    """
    skeleton_bool = skeletonize(cleaned_mask > 0)
    return (skeleton_bool.astype(np.uint8)) * 255


def process_road_network(
    mask_path: Optional[Union[str, Path]] = None,
    sat_path: Optional[Union[str, Path]] = None,
    output_dir: Optional[Union[str, Path]] = None,
    road_threshold: float = ROAD_THRESHOLD,
    min_component_size: int = MIN_COMPONENT_SIZE,
) -> Dict[str, str]:
    """Execute complete road network extraction pipeline and export debug outputs.

    Args:
        mask_path: Optional path to binary road prediction mask.
        sat_path: Optional path to satellite image.
        output_dir: Optional directory to save output files.
        road_threshold: Binarization probability threshold.
        min_component_size: Minimum component pixel size to keep.

    Returns:
        Dict[str, str]: Dictionary of saved debug file paths.
    """
    s_path = Path(sat_path) if sat_path else DEFAULT_SAT_PATH
    if not s_path.exists():
        raise FileNotFoundError(f"Input satellite image not found at '{s_path}'")

    out_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_mask = None
    if mask_path:
        m_path = Path(mask_path)
        if m_path.exists():
            raw_mask = cv2.imread(str(m_path), cv2.IMREAD_GRAYSCALE)

    # If no explicit mask path provided or mask could not be loaded/is blank, run prediction for s_path
    if raw_mask is None or np.max(raw_mask) == 0:
        from ai.predict import predict
        print(f"[INFO] Generating U-Net road damage prediction for input image: '{s_path.name}'...")
        pred_res = predict(image_path=s_path, output_dir=out_dir, threshold=road_threshold)
        m_path = Path(pred_res["mask_output_path"])
        raw_mask = cv2.imread(str(m_path), cv2.IMREAD_GRAYSCALE)

    if raw_mask is None:
        raise ValueError(f"Failed to read or generate mask for satellite image '{s_path}'")

    cleaned_mask = clean_road_mask(
        raw_mask,
        road_threshold=road_threshold,
        min_component_size=min_component_size,
    )
    skeleton = extract_road_skeleton(cleaned_mask)

    # Save Debug Outputs
    img_prefix = f"{s_path.stem}_" if sat_path else ""
    cleaned_mask_path = out_dir / f"{img_prefix}road_mask_cleaned.png"
    cv2.imwrite(str(cleaned_mask_path), cleaned_mask)

    skeleton_path = out_dir / f"{img_prefix}road_skeleton.png"
    cv2.imwrite(str(skeleton_path), skeleton)

    # Save standard location as well for backward compatibility
    cv2.imwrite(str(out_dir / "road_mask_cleaned.png"), cleaned_mask)
    cv2.imwrite(str(out_dir / "road_skeleton.png"), skeleton)

    overlay_path = out_dir / f"{img_prefix}road_network_overlay.png"
    sat_img = Image.open(s_path).convert("RGB").resize((raw_mask.shape[1], raw_mask.shape[0]))
    overlay = np.array(sat_img)
    # Red centerlines on satellite image
    overlay[skeleton > 0] = [255, 0, 0]
    Image.fromarray(overlay).save(overlay_path)
    Image.fromarray(overlay).save(out_dir / "road_network_overlay.png")

    return {
        "road_mask_cleaned.png": str(cleaned_mask_path),
        "road_skeleton.png": str(skeleton_path),
        "road_network_overlay.png": str(overlay_path),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RESQROUTE AI Road Network Extraction & Skeletonization")
    parser.add_argument("--image", "--sat", type=str, default=None, help="Path to input satellite image")
    parser.add_argument("--mask", type=str, default=None, help="Path to prediction mask image")
    parser.add_argument("--output_dir", type=str, default=None, help="Directory to save output files")
    parser.add_argument("--threshold", type=float, default=ROAD_THRESHOLD, help="Binarization threshold (default 0.40)")
    args = parser.parse_args()

    print("=" * 60)
    print("       RESQROUTE AI - ROAD NETWORK EXTRACTION")
    print("=" * 60)
    res = process_road_network(
        sat_path=args.image,
        mask_path=args.mask,
        output_dir=args.output_dir,
        road_threshold=args.threshold,
    )
    print("[SUCCESS] Mask cleaning & skeletonization complete!")
    print(f"  - Cleaned Mask : {res['road_mask_cleaned.png']}")
    print(f"  - Skeleton     : {res['road_skeleton.png']}")
    print(f"  - Overlay      : {res['road_network_overlay.png']}")
    print("=" * 60)