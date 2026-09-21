"""
Sample Visualization Generator for Preprocessed SpaceNet Road Dataset.

Generates at least 10 sample visualizations showing original satellite imagery
side-by-side with road mask overlays, as well as a grid contact sheet.
"""

import os
import glob
import random
import logging
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

from .config import (
    PROCESSED_IMAGES_DIR,
    PROCESSED_MASKS_DIR,
    PROCESSED_VISUALIZATIONS_DIR,
    NUM_VISUALIZATION_SAMPLES,
    RANDOM_SEED,
    ROAD_VAL,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Visualizer")


def create_overlay_image(img_bgr: np.ndarray, mask: np.ndarray, alpha: float = 0.5) -> np.ndarray:
    """
    Create a vibrant green road overlay on top of satellite imagery.
    
    Args:
        img_bgr: Original satellite image (H, W, 3) in BGR order
        mask: Binary gray mask (H, W) where road pixels are >= 128
        alpha: Transparency blending factor for road overlay
    """
    overlay = img_bgr.copy()
    road_indices = mask >= (ROAD_VAL / 2.0)
    
    # Create vibrant green color mask (BGR: [0, 255, 0])
    color_mask = np.zeros_like(img_bgr)
    color_mask[road_indices] = [0, 255, 0]  # Bright green

    # Blend original image with color mask where road exists
    blended = cv2.addWeighted(img_bgr, 1.0 - alpha, color_mask, alpha, 0)
    overlay[road_indices] = blended[road_indices]

    # Draw thin contour outlines around road boundaries for maximum visual crispness
    contours, _ = cv2.findContours((mask >= 128).astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, contours, -1, (0, 255, 255), 1)  # Yellow contour border

    return overlay


def create_side_by_side_panel(img_bgr: np.ndarray, overlay_bgr: np.ndarray, chip_id: str) -> np.ndarray:
    """
    Create a clean side-by-side comparison panel with titles.
    
    LEFT: Original PS-RGB Image
    RIGHT: Satellite Image + Road Overlay
    """
    h, w, c = img_bgr.shape
    
    # Header bar height
    header_h = 50
    panel_w = w * 2
    panel_h = h + header_h

    panel = np.zeros((panel_h, panel_w, 3), dtype=np.uint8)

    # Header bar background (Dark navy)
    panel[:header_h, :] = [30, 20, 20]

    # Place left and right images
    panel[header_h:, :w] = img_bgr
    panel[header_h:, w:] = overlay_bgr

    # Add text headers
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(panel, f"Chip: {chip_id} | Original PS-RGB", (20, 32), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(panel, "Road Mask Overlay (Green)", (w + 20, 32), font, 0.7, (0, 255, 255), 2, cv2.LINE_AA)

    # Dividing line down middle
    cv2.line(panel, (w, 0), (w, panel_h), (255, 255, 255), 2)

    return panel


def generate_visualizations(num_samples: int = NUM_VISUALIZATION_SAMPLES) -> List[Path]:
    """Generate individual sample visualizations and a grid contact sheet."""
    PROCESSED_VISUALIZATIONS_DIR.mkdir(parents=True, exist_ok=True)

    img_paths = sorted(glob.glob(str(PROCESSED_IMAGES_DIR / "*.png")))
    if not img_paths:
        raise FileNotFoundError(f"No processed images found in {PROCESSED_IMAGES_DIR}. Run preprocessor first!")

    # Select chips with non-empty roads for compelling visualizations
    candidate_chips: List[Tuple[str, int]] = []
    for img_p in img_paths:
        chip_id = Path(img_p).stem
        mask_p = PROCESSED_MASKS_DIR / f"{chip_id}.png"
        if mask_p.exists():
            mask = cv2.imread(str(mask_p), cv2.IMREAD_GRAYSCALE)
            road_count = int((mask >= 128).sum())
            if road_count > 1000:  # Has significant road presence
                candidate_chips.append((chip_id, road_count))

    # Sort candidates by road pixel count (descending) or sample deterministically
    candidate_chips.sort(key=lambda x: x[1], reverse=True)

    rand = random.Random(RANDOM_SEED)
    selected_chips: List[str] = []

    if len(candidate_chips) >= num_samples:
        # Pick top 5 with highest road density + 5 random non-empty
        selected_chips.extend([c[0] for c in candidate_chips[:5]])
        remaining = candidate_chips[5:]
        rand.shuffle(remaining)
        selected_chips.extend([c[0] for c in remaining[: (num_samples - 5)]])
    else:
        selected_chips = [Path(p).stem for p in img_paths[:num_samples]]

    saved_samples: List[Path] = []
    panels: List[np.ndarray] = []

    logger.info(f"Generating {len(selected_chips)} visualization samples...")

    for idx, chip_id in enumerate(selected_chips, 1):
        img_p = PROCESSED_IMAGES_DIR / f"{chip_id}.png"
        mask_p = PROCESSED_MASKS_DIR / f"{chip_id}.png"

        img_bgr = cv2.imread(str(img_p))
        mask = cv2.imread(str(mask_p), cv2.IMREAD_GRAYSCALE)

        overlay = create_overlay_image(img_bgr, mask)
        panel = create_side_by_side_panel(img_bgr, overlay, chip_id)

        sample_path = PROCESSED_VISUALIZATIONS_DIR / f"sample_{idx:02d}_{chip_id}.png"
        cv2.imwrite(str(sample_path), panel)
        saved_samples.append(sample_path)

        # Resize for contact sheet grid
        h, w, c = panel.shape
        resized_panel = cv2.resize(panel, (640, int(640 * h / w)))
        panels.append(resized_panel)

        logger.info(f"Saved sample {idx}/{len(selected_chips)}: {sample_path.name}")

    # Generate Contact Sheet (Grid)
    if panels:
        cols = 2
        rows = (len(panels) + cols - 1) // cols
        pw, ph = panels[0].shape[1], panels[0].shape[0]

        contact_sheet = np.zeros((rows * ph, cols * pw, 3), dtype=np.uint8)

        for i, p in enumerate(panels):
            r = i // cols
            c = i % cols
            contact_sheet[r * ph : (r + 1) * ph, c * pw : (c + 1) * pw] = p

        contact_path = PROCESSED_VISUALIZATIONS_DIR / "contact_sheet.png"
        cv2.imwrite(str(contact_path), contact_sheet)
        logger.info(f"Saved contact sheet grid to: {contact_path}")

    return saved_samples


if __name__ == "__main__":
    generate_visualizations()
