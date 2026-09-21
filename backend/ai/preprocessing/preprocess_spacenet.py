"""
SpaceNet 5 Mumbai Road Dataset Preprocessing Pipeline.

Pairs PS-RGB satellite tiles with GeoJSON road speed annotations,
converts road LineString/MultiLineString geometries into aligned binary masks,
splits dataset into 80/20 train/val sets, and outputs dataset_summary.json.
"""

import os
import json
import glob
import random
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any

import cv2
import numpy as np
import rasterio
from rasterio.features import rasterize
from shapely.geometry import shape

from .config import (
    RAW_DATASET_DIR,
    PS_RGB_DIR,
    GEOJSON_DIR,
    PROCESSED_DATASET_DIR,
    PROCESSED_IMAGES_DIR,
    PROCESSED_MASKS_DIR,
    PROCESSED_VISUALIZATIONS_DIR,
    TRAIN_TXT,
    VAL_TXT,
    DATASET_SUMMARY_JSON,
    ROAD_BUFFER_PIXELS,
    BACKGROUND_VAL,
    ROAD_VAL,
    EXPECTED_WIDTH,
    EXPECTED_HEIGHT,
    EXPECTED_CHANNELS,
    TRAIN_SPLIT_RATIO,
    RANDOM_SEED,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SpaceNetPreprocessor")


def setup_directories() -> None:
    """Create all required output directories."""
    PROCESSED_DATASET_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_MASKS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_VISUALIZATIONS_DIR.mkdir(parents=True, exist_ok=True)


def match_image_label_pairs() -> Tuple[Dict[str, Path], Dict[str, Path], List[str], List[str], List[str]]:
    """
    Match PS-RGB satellite tiles with corresponding GeoJSON road label files.
    
    Returns:
        matched_dict (chip_id -> (img_path, json_path))
        unmatched_images (list of paths)
        unmatched_labels (list of paths)
    """
    img_files = sorted(glob.glob(str(PS_RGB_DIR / "*.tif")))
    json_files = sorted(glob.glob(str(GEOJSON_DIR / "*.geojson")))

    img_map: Dict[str, Path] = {}
    for f in img_files:
        p = Path(f)
        chip_id = p.name.replace("SN5_roads_train_AOI_8_Mumbai_PS-RGB_", "").replace(".tif", "")
        img_map[chip_id] = p

    json_map: Dict[str, Path] = {}
    for f in json_files:
        p = Path(f)
        chip_id = p.name.replace("SN5_roads_train_AOI_8_Mumbai_geojson_roads_speed_", "").replace(".geojson", "")
        json_map[chip_id] = p

    img_keys = set(img_map.keys())
    json_keys = set(json_map.keys())

    matched_keys = sorted(list(img_keys.intersection(json_keys)))
    unmatched_img_keys = sorted(list(img_keys - json_keys))
    unmatched_json_keys = sorted(list(json_keys - img_keys))

    unmatched_images = [str(img_map[k]) for k in unmatched_img_keys]
    unmatched_labels = [str(json_map[k]) for k in unmatched_json_keys]

    logger.info(f"Total satellite images: {len(img_files)}")
    logger.info(f"Total GeoJSON labels:   {len(json_files)}")
    logger.info(f"Matched pairs:          {len(matched_keys)}")
    logger.info(f"Unmatched images:       {len(unmatched_images)}")
    logger.info(f"Unmatched labels:       {len(unmatched_labels)}")

    if len(matched_keys) == 0:
        raise RuntimeError("No matching image and label pairs found! Check directory structure and naming conventions.")

    return img_map, json_map, matched_keys, unmatched_images, unmatched_labels


def geojson_to_raster_mask(
    geojson_path: Path,
    transform: rasterio.Affine,
    width: int,
    height: int,
    buffer_pixels: float = ROAD_BUFFER_PIXELS
) -> Tuple[np.ndarray, int, List[str]]:
    """
    Convert GeoJSON LineString/MultiLineString annotations to a binary raster mask.
    
    Args:
        geojson_path: Path to GeoJSON file
        transform: GeoTIFF affine transform
        width: Mask width in pixels
        height: Mask height in pixels
        buffer_pixels: Road buffering radius in pixels
        
    Returns:
        mask (np.ndarray): Binary uint8 mask (BACKGROUND_VAL=0, ROAD_VAL=255)
        num_features (int): Number of valid line features processed
        errors (list): Geometry parsing errors, if any
    """
    errors: List[str] = []
    
    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            gj_data = json.load(f)
    except Exception as e:
        err_msg = f"Corrupt or invalid GeoJSON file {geojson_path.name}: {e}"
        logger.error(err_msg)
        errors.append(err_msg)
        return np.zeros((height, width), dtype=np.uint8), 0, errors

    features = gj_data.get("features", [])
    valid_buffered_geoms = []
    
    # Calculate degree buffer distance based on pixel scale transform.a
    buffer_deg = buffer_pixels * transform.a

    for idx, feat in enumerate(features):
        geom_dict = feat.get("geometry")
        if not geom_dict:
            continue
        try:
            geom = shape(geom_dict)
            if geom.is_empty or not geom.is_valid:
                continue
            if geom.geom_type in ["LineString", "MultiLineString"]:
                buffered = geom.buffer(buffer_deg)
                valid_buffered_geoms.append(buffered)
        except Exception as e:
            err_msg = f"Geometry parsing error in {geojson_path.name} feature {idx}: {e}"
            logger.warning(err_msg)
            errors.append(err_msg)

    if not valid_buffered_geoms:
        # Empty road annotation
        mask = np.full((height, width), BACKGROUND_VAL, dtype=np.uint8)
        return mask, 0, errors

    shapes = [(g, ROAD_VAL) for g in valid_buffered_geoms]
    mask = rasterize(
        shapes=shapes,
        out_shape=(height, width),
        transform=transform,
        fill=BACKGROUND_VAL,
        dtype=np.uint8,
    )

    return mask, len(valid_buffered_geoms), errors


def run_preprocessing() -> Dict[str, Any]:
    """Execute the complete dataset preprocessing pipeline."""
    setup_directories()

    img_map, json_map, matched_keys, unmatched_images, unmatched_labels = match_image_label_pairs()

    total_road_pixels = 0
    total_mask_pixels = 0
    preprocessing_errors: List[str] = []
    processed_count = 0

    # Deterministic train/validation split
    random_inst = random.Random(RANDOM_SEED)
    shuffled_keys = list(matched_keys)
    random_inst.shuffle(shuffled_keys)

    split_idx = int(len(shuffled_keys) * TRAIN_SPLIT_RATIO)
    train_keys = sorted(shuffled_keys[:split_idx])
    val_keys = sorted(shuffled_keys[split_idx:])

    logger.info(f"Splitting dataset: {len(train_keys)} train, {len(val_keys)} validation")

    # Write train.txt and val.txt
    with open(TRAIN_TXT, "w", encoding="utf-8") as f:
        for k in train_keys:
            f.write(f"{k}\n")

    with open(VAL_TXT, "w", encoding="utf-8") as f:
        for k in val_keys:
            f.write(f"{k}\n")

    logger.info(f"Processing {len(matched_keys)} tile pairs...")

    for idx, chip_id in enumerate(matched_keys, 1):
        img_path = img_map[chip_id]
        json_path = json_map[chip_id]

        try:
            with rasterio.open(img_path) as src:
                width, height = src.width, src.height
                channels = src.count
                transform = src.transform
                
                # Read PS-RGB image (RGB order)
                img_data = src.read([1, 2, 3])  # Read bands 1, 2, 3
                img_data = np.transpose(img_data, (1, 2, 0))  # (H, W, C)

            # Data Validation: Dimensions
            if (width, height, channels) != (EXPECTED_WIDTH, EXPECTED_HEIGHT, EXPECTED_CHANNELS):
                err_msg = f"Dimension mismatch in {img_path.name}: got ({width}, {height}, {channels}), expected ({EXPECTED_WIDTH}, {EXPECTED_HEIGHT}, {EXPECTED_CHANNELS})"
                logger.error(err_msg)
                preprocessing_errors.append(err_msg)

        except Exception as e:
            err_msg = f"Corrupt image file {img_path.name}: {e}"
            logger.error(err_msg)
            preprocessing_errors.append(err_msg)
            continue

        # Convert GeoJSON to binary mask
        mask, num_feats, mask_errors = geojson_to_raster_mask(json_path, transform, width, height)
        preprocessing_errors.extend(mask_errors)

        # Dimension check between image and mask
        if mask.shape != (height, width):
            err_msg = f"Image/Mask dimension mismatch for {chip_id}: image shape ({height}, {width}), mask shape {mask.shape}"
            logger.error(err_msg)
            preprocessing_errors.append(err_msg)
            continue

        # Save processed PS-RGB image as PNG (convert RGB to BGR for OpenCV)
        out_img_path = PROCESSED_IMAGES_DIR / f"{chip_id}.png"
        out_mask_path = PROCESSED_MASKS_DIR / f"{chip_id}.png"

        bgr_img = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(out_img_path), bgr_img)
        cv2.imwrite(str(out_mask_path), mask)

        # Statistics
        road_px = int((mask == ROAD_VAL).sum())
        total_road_pixels += road_px
        total_mask_pixels += (width * height)
        processed_count += 1

        if idx % 100 == 0 or idx == len(matched_keys):
            logger.info(f"Processed {idx}/{len(matched_keys)} tiles...")

    avg_road_pct = (total_road_pixels / total_mask_pixels * 100.0) if total_mask_pixels > 0 else 0.0

    summary_data = {
        "total_images": len(img_map),
        "total_labels": len(json_map),
        "matched_pairs": len(matched_keys),
        "unmatched_images": len(unmatched_images),
        "unmatched_labels": len(unmatched_labels),
        "image_width": EXPECTED_WIDTH,
        "image_height": EXPECTED_HEIGHT,
        "train_count": len(train_keys),
        "validation_count": len(val_keys),
        "total_road_pixels": total_road_pixels,
        "average_road_percentage": round(avg_road_pct, 4),
        "preprocessing_errors": preprocessing_errors,
    }

    with open(DATASET_SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    logger.info(f"Saved summary report to {DATASET_SUMMARY_JSON}")

    # Final Report
    print("\n" + "=" * 50)
    print("DATASET PREPROCESSING COMPLETE")
    print("=" * 50)
    print(f"Images:                   {summary_data['total_images']}")
    print(f"Labels:                   {summary_data['total_labels']}")
    print(f"Matched:                  {summary_data['matched_pairs']}")
    print(f"Train:                    {summary_data['train_count']}")
    print(f"Validation:               {summary_data['validation_count']}")
    print(f"Image size:               {EXPECTED_WIDTH}x{EXPECTED_HEIGHT}x{EXPECTED_CHANNELS}")
    print(f"Average road coverage:    {summary_data['average_road_percentage']:.2f}%")
    print(f"Generated images:         {processed_count}")
    print(f"Generated masks:          {processed_count}")
    print(f"Preprocessing Errors:     {len(preprocessing_errors)}")
    print("=" * 50 + "\n")

    return summary_data


if __name__ == "__main__":
    run_preprocessing()
