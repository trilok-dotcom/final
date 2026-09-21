"""
PyTorch Dataset module for preprocessed SpaceNet 5 Mumbai Road Segmentation dataset.
"""

import os
from pathlib import Path
from typing import Optional, Tuple, Callable

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset

from .config import (
    PROCESSED_IMAGES_DIR,
    PROCESSED_MASKS_DIR,
    TRAIN_TXT,
    VAL_TXT,
    ROAD_VAL,
)


class SpaceNetRoadDataset(Dataset):
    """
    PyTorch Dataset for loading preprocessed SpaceNet satellite imagery and binary road masks.
    
    Args:
        split (str): 'train' or 'val'
        transform (Callable, optional): Albumentations or PyTorch transformation pipeline
        normalize (bool): If True, normalizes image pixels to [0, 1] range (float32).
    """

    def __init__(
        self,
        split: str = "train",
        transform: Optional[Callable] = None,
        normalize: bool = True,
    ) -> None:
        super().__init__()
        self.split = split.lower()
        self.transform = transform
        self.normalize = normalize

        if self.split == "train":
            split_file = TRAIN_TXT
        elif self.split in ["val", "validation"]:
            split_file = VAL_TXT
        else:
            raise ValueError(f"Invalid split '{split}'. Expected 'train' or 'val'.")

        if not split_file.exists():
            raise FileNotFoundError(
                f"Split file '{split_file}' not found. Run dataset preprocessing first using "
                f"'python -m backend.ai.preprocessing.preprocess_spacenet'."
            )

        with open(split_file, "r", encoding="utf-8") as f:
            self.chip_ids = [line.strip() for line in f if line.strip()]

        if not self.chip_ids:
            raise ValueError(f"Split file '{split_file}' is empty!")

    def __len__(self) -> int:
        return len(self.chip_ids)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        chip_id = self.chip_ids[idx]
        img_path = PROCESSED_IMAGES_DIR / f"{chip_id}.png"
        mask_path = PROCESSED_MASKS_DIR / f"{chip_id}.png"

        if not img_path.exists():
            raise FileNotFoundError(f"Processed image missing for chip '{chip_id}': {img_path}")
        if not mask_path.exists():
            raise FileNotFoundError(f"Processed mask missing for chip '{chip_id}': {mask_path}")

        # Read image (RGB order)
        bgr = cv2.imread(str(img_path))
        if bgr is None:
            raise ValueError(f"Corrupt or unreadable image file: {img_path}")
        img = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

        # Read single-channel binary mask
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask is None:
            raise ValueError(f"Corrupt or unreadable mask file: {mask_path}")

        # Convert mask to binary [0, 1]
        binary_mask = (mask >= (ROAD_VAL / 2.0)).astype(np.float32)

        # Apply Albumentations or custom transform if provided
        if self.transform is not None:
            augmented = self.transform(image=img, mask=binary_mask)
            img = augmented["image"]
            binary_mask = augmented["mask"]

        # Convert numpy arrays to PyTorch tensors if not already done by transform
        if isinstance(img, np.ndarray):
            if self.normalize:
                img = img.astype(np.float32) / 255.0
            # Convert (H, W, C) -> (C, H, W)
            img_tensor = torch.from_numpy(img).permute(2, 0, 1).float()
        else:
            img_tensor = img

        if isinstance(binary_mask, np.ndarray):
            # Convert (H, W) -> (1, H, W)
            mask_tensor = torch.from_numpy(binary_mask).unsqueeze(0).float()
        else:
            mask_tensor = binary_mask

        return img_tensor, mask_tensor
