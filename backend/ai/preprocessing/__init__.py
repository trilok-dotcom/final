"""
RESQROUTE SpaceNet Mumbai Dataset Preprocessing Package.

Provides tools to preprocess SpaceNet 5 satellite imagery (PS-RGB)
and road vector GeoJSON annotations into binary raster segmentation masks.
"""

from .config import (
    RAW_DATASET_DIR,
    PROCESSED_DATASET_DIR,
    ROAD_BUFFER_PIXELS,
    BACKGROUND_VAL,
    ROAD_VAL,
    RANDOM_SEED,
)

__all__ = [
    "RAW_DATASET_DIR",
    "PROCESSED_DATASET_DIR",
    "ROAD_BUFFER_PIXELS",
    "BACKGROUND_VAL",
    "ROAD_VAL",
    "RANDOM_SEED",
]
