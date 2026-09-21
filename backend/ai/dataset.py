import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Union
import cv2
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
import albumentations as A
from albumentations.pytorch import ToTensorV2

# Ensure backend parent directory is in sys.path for standalone script execution
AI_DIR = Path(__file__).resolve().parent
BACKEND_DIR = AI_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ai import config


def get_default_transforms(
    split: str = "train",
    image_height: int = config.IMAGE_HEIGHT,
    image_width: int = config.IMAGE_WIDTH,
) -> A.Compose:
    """Return default Albumentations image augmentation pipeline.

    Args:
        split (str): Dataset split ('train', 'valid', or 'test').
        image_height (int): Target resize height.
        image_width (int): Target resize width.

    Returns:
        A.Compose: Albumentations composition transform pipeline.
    """
    if split == "train":
        return A.Compose(
            [
                A.Resize(height=image_height, width=image_width),
                A.HorizontalFlip(p=0.5),
                A.VerticalFlip(p=0.5),
                A.RandomRotate90(p=0.5),
                A.ShiftScaleRotate(
                    shift_limit=0.0625, scale_limit=0.1, rotate_limit=45, p=0.5
                ),
                A.Normalize(
                    mean=config.NORM_MEAN,
                    std=config.NORM_STD,
                    max_pixel_value=255.0,
                ),
                ToTensorV2(),
            ]
        )
    else:
        # Validation / Testing evaluation transforms (no random augmentations)
        return A.Compose(
            [
                A.Resize(height=image_height, width=image_width),
                A.Normalize(
                    mean=config.NORM_MEAN,
                    std=config.NORM_STD,
                    max_pixel_value=255.0,
                ),
                ToTensorV2(),
            ]
        )


class SatelliteRoadDataset(Dataset):
    """PyTorch Dataset for Satellite Image Binary Road Segmentation.

    Pairs satellite images (*_sat.jpg/png) with matching ground truth masks (*_mask.png).
    Supports train, valid, and test dataset splits with Albumentations augmentation.
    """

    def __init__(
        self,
        split: str = "train",
        data_dir: Optional[Union[str, Path]] = None,
        transform: Optional[A.Compose] = None,
        is_test: bool = False,
    ) -> None:
        """
        Args:
            split (str): Split category ('train', 'valid', or 'test').
            data_dir (Optional[str | Path]): Path to dataset split directory. If None, defaults to config directory.
            transform (Optional[A.Compose]): Albumentations transforms.
            is_test (bool): If True, allows missing masks for test evaluation mode.
        """
        self.split = split.lower()
        self.is_test = is_test or (self.split == "test")

        if data_dir:
            self.split_dir = Path(data_dir)
        else:
            if self.split == "train":
                self.split_dir = config.TRAIN_DIR
            elif self.split == "valid" or self.split == "val":
                self.split_dir = config.VALID_DIR
            elif self.split == "test":
                self.split_dir = config.TEST_DIR
            else:
                self.split_dir = config.DATASETS_DIR / self.split

        self.transform = transform or get_default_transforms(
            split=self.split
        )

        self.paired_files: List[Tuple[Path, Optional[Path]]] = []
        self._find_and_pair_samples()

    def _find_and_pair_samples(self) -> None:
        """Scan directory and pair *_sat image files with matching *_mask files."""
        if not self.split_dir.exists():
            print(
                f"[WARNING] Dataset split directory '{self.split_dir}' does not exist."
            )
            return

        all_files = list(self.split_dir.glob("*"))

        # Find satellite image candidates ending with config.SAT_SUFFIX
        sat_images: List[Path] = []
        for file in all_files:
            if file.is_file() and file.suffix.lower() in config.SUPPORTED_IMG_EXTENSIONS:
                stem = file.stem  # e.g., '104_sat'
                if stem.endswith(config.SAT_SUFFIX):
                    sat_images.append(file)

        sat_images.sort()

        paired_count = 0
        missing_mask_count = 0

        for sat_path in sat_images:
            stem = sat_path.stem  # '104_sat'
            prefix = stem[: -len(config.SAT_SUFFIX)]  # '104'

            # Look for matching mask (e.g., '104_mask.png')
            mask_path: Optional[Path] = None
            for ext in config.SUPPORTED_MASK_EXTENSIONS:
                candidate = self.split_dir / f"{prefix}{config.MASK_SUFFIX}{ext}"
                if candidate.exists() and candidate.is_file():
                    mask_path = candidate
                    break

            if mask_path is not None:
                self.paired_files.append((sat_path, mask_path))
                paired_count += 1
            else:
                missing_mask_count += 1
                if self.is_test:
                    # In test mode, mask is optional
                    self.paired_files.append((sat_path, None))
                else:
                    print(
                        f"[WARNING] Missing mask for satellite image '{sat_path.name}'. Expected '{prefix}{config.MASK_SUFFIX}.png'. Skipping pair."
                    )

        print(
            f"[INFO] Loaded '{self.split}' dataset split: {paired_count} paired samples found in '{self.split_dir}'."
        )
        if missing_mask_count > 0 and not self.is_test:
            print(
                f"[WARNING] {missing_mask_count} satellite images were skipped due to missing mask files."
            )

    def __len__(self) -> int:
        return len(self.paired_files)

    def __getitem__(self, idx: int) -> Union[Tuple[torch.Tensor, torch.Tensor], Tuple[torch.Tensor, str]]:
        sat_path, mask_path = self.paired_files[idx]

        # 1. Read Satellite Image (RGB)
        sat_img = cv2.imread(str(sat_path), cv2.IMREAD_COLOR)
        if sat_img is None:
            raise FileNotFoundError(
                f"Failed to load satellite image at path: {sat_path}"
            )
        sat_img = cv2.cvtColor(sat_img, cv2.COLOR_BGR2RGB)

        # 2. Read Binary Mask if available
        if mask_path is not None and mask_path.exists():
            mask_img = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
            if mask_img is None:
                raise FileNotFoundError(f"Failed to load mask image at path: {mask_path}")
            # Binarize mask to 0 or 255
            _, mask_img = cv2.threshold(mask_img, 127, 255, cv2.THRESH_BINARY)
        else:
            # Create dummy mask if testing without ground truth
            mask_img = np.zeros((sat_img.shape[0], sat_img.shape[1]), dtype=np.uint8)

        # 3. Apply Albumentations Transformations
        augmented = self.transform(image=sat_img, mask=mask_img)
        image_tensor = augmented["image"]  # Shape: (3, H, W), dtype: float32 normalized
        mask_tensor = augmented["mask"]    # Shape: (H, W), dtype: uint8 or float32

        # Ensure mask tensor is float32 binary tensor with shape (1, H, W) in range [0.0, 1.0]
        if isinstance(mask_tensor, torch.Tensor):
            mask_tensor = mask_tensor.unsqueeze(0).float()
            if mask_tensor.max() > 1.0:
                mask_tensor = mask_tensor / 255.0
            mask_tensor = (mask_tensor > 0.5).float()
        else:
            mask_arr = (mask_img > 127).astype(np.float32)
            mask_tensor = torch.from_numpy(mask_arr).unsqueeze(0)

        if self.is_test and mask_path is None:
            return image_tensor, sat_path.name

        return image_tensor, mask_tensor


def get_dataloaders(
    batch_size: int = config.BATCH_SIZE,
    num_workers: int = config.NUM_WORKERS,
    pin_memory: bool = config.PIN_MEMORY,
) -> Dict[str, DataLoader]:
    """Create PyTorch DataLoaders for train, valid, and test splits.

    Returns:
        Dict[str, DataLoader]: Dictionary mapping split names to DataLoaders.
    """
    dataloaders = {}
    for split in ["train", "valid", "test"]:
        dataset = SatelliteRoadDataset(split=split)
        shuffle = (split == "train")
        dataloaders[split] = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=shuffle,
            num_workers=num_workers,
            pin_memory=pin_memory,
        )
    return dataloaders


if __name__ == "__main__":
    print("==================================================")
    print("      RESQROUTE AI - Dataset Pipeline Test        ")
    print("==================================================")

    # 1. Ensure test dataset directories exist
    config.TRAIN_DIR.mkdir(parents=True, exist_ok=True)

    # If train directory is empty, generate sample dummy images to test loader
    train_files = list(config.TRAIN_DIR.glob("*"))
    if not train_files:
        print(f"[SETUP] Generating dummy sample images in '{config.TRAIN_DIR}'...")
        dummy_sat = np.full((512, 512, 3), (34, 139, 34), dtype=np.uint8)
        cv2.line(dummy_sat, (0, 256), (512, 256), (128, 128, 128), 16)
        dummy_mask = np.zeros((512, 512), dtype=np.uint8)
        cv2.line(dummy_mask, (0, 256), (512, 256), 255, 16)

        cv2.imwrite(str(config.TRAIN_DIR / "104_sat.jpg"), cv2.cvtColor(dummy_sat, cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(config.TRAIN_DIR / "104_mask.png"), dummy_mask)
        cv2.imwrite(str(config.TRAIN_DIR / "105_sat.jpg"), cv2.cvtColor(dummy_sat, cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(config.TRAIN_DIR / "105_mask.png"), dummy_mask)
        print("[SETUP] Created dummy samples: 104_sat.jpg <-> 104_mask.png, 105_sat.jpg <-> 105_mask.png")

    # 2. Instantiate SatelliteRoadDataset for train split
    dataset = SatelliteRoadDataset(split="train")
    print(f"[TEST] Dataset total paired samples: {len(dataset)}")

    if len(dataset) > 0:
        # 3. Create DataLoader and fetch 1 batch
        dataloader = DataLoader(dataset, batch_size=2, shuffle=True)
        images, masks = next(iter(dataloader))

        print("\n--- Batch Inspection ---")
        print(f"Image Batch Tensor Shape : {images.shape} (Type: {images.dtype})")
        print(f"Mask Batch Tensor Shape  : {masks.shape}  (Type: {masks.dtype})")
        print(f"Image Min / Max Values   : Min={images.min():.4f}, Max={images.max():.4f}")
        print(f"Mask Min / Max Values    : Min={masks.min():.4f}, Max={masks.max():.4f}")
        print(f"Unique Mask Tensor Values: {torch.unique(masks).tolist()}")
        print("\n[SUCCESS] PyTorch Dataset & Albumentations pipeline verified!")
    else:
        print("[WARNING] No paired samples found in dataset path.")
