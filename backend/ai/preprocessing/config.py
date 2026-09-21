"""
Configuration parameters for SpaceNet 5 Mumbai Road Preprocessing.
"""

import os
from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]

RAW_DATASET_DIR = PROJECT_ROOT / "backend" / "ai" / "dataset2" / "nfs" / "data" / "cosmiq" / "spacenet" / "competitions" / "SN5_roads" / "tiles_upload" / "train" / "AOI_8_Mumbai"
PS_RGB_DIR = RAW_DATASET_DIR / "PS-RGB"
GEOJSON_DIR = RAW_DATASET_DIR / "geojson_roads_speed"

# Processed Output Directory Structure
PROCESSED_DATASET_DIR = PROJECT_ROOT / "backend" / "ai" / "datasets" / "processed"
PROCESSED_IMAGES_DIR = PROCESSED_DATASET_DIR / "images"
PROCESSED_MASKS_DIR = PROCESSED_DATASET_DIR / "masks"
PROCESSED_VISUALIZATIONS_DIR = PROCESSED_DATASET_DIR / "visualizations"

TRAIN_TXT = PROCESSED_DATASET_DIR / "train.txt"
VAL_TXT = PROCESSED_DATASET_DIR / "val.txt"
DATASET_SUMMARY_JSON = PROCESSED_DATASET_DIR / "dataset_summary.json"

# Rasterization & Masking Parameters
# Road annotations in SpaceNet are 1D centerlines.
# ROAD_BUFFER_PIXELS defines the buffering radius (in pixel units).
# A buffer radius of 4.0 creates an 8-pixel wide road mask (~2.5 meters in real world).
ROAD_BUFFER_PIXELS: float = 4.0

BACKGROUND_VAL: int = 0
ROAD_VAL: int = 255

# Raster Metadata Expectations
EXPECTED_WIDTH: int = 1300
EXPECTED_HEIGHT: int = 1300
EXPECTED_CHANNELS: int = 3

# Dataset Split Parameters
TRAIN_SPLIT_RATIO: float = 0.8
VAL_SPLIT_RATIO: float = 0.2
RANDOM_SEED: int = 42

# Sample Visualization Parameters
NUM_VISUALIZATION_SAMPLES: int = 10
