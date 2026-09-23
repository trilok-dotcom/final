import sys
from pathlib import Path
from typing import Union, Tuple
import cv2
import numpy as np
import torch
from PIL import Image

AI_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = AI_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ai import config

# ImageNet normalization constants used during training
NORM_MEAN = np.array(config.NORM_MEAN, dtype=np.float32)
NORM_STD = np.array(config.NORM_STD, dtype=np.float32)


def load_image_raw_rgb(
    image_input: Union[str, Path, np.ndarray, Image.Image]
) -> np.ndarray:
    """Load image input into original RGB uint8 numpy array of shape (H, W, 3) without resizing."""
    img_rgb: np.ndarray

    if isinstance(image_input, (str, Path)):
        img_path = Path(image_input)
        if not img_path.exists():
            raise FileNotFoundError(f"Satellite image file not found at '{img_path}'")
        
        img_bgr = cv2.imread(str(img_path), cv2.IMREAD_UNCHANGED)
        if img_bgr is None:
            raise ValueError(f"Failed to read image at '{img_path}'. File may be corrupted or unsupported.")
        
        if img_bgr.ndim == 2:
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_GRAY2RGB)
        elif img_bgr.ndim == 3 and img_bgr.shape[2] == 4:
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGRA2RGB)
        elif img_bgr.ndim == 3 and img_bgr.shape[2] == 3:
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        else:
            raise ValueError(f"Unsupported image shape/channels: {img_bgr.shape}")

    elif isinstance(image_input, Image.Image):
        img_rgb = np.array(image_input.convert("RGB"))

    elif isinstance(image_input, np.ndarray):
        if image_input.size == 0:
            raise ValueError("Input image array is empty.")
        
        if image_input.ndim == 2:
            img_rgb = cv2.cvtColor(image_input, cv2.COLOR_GRAY2RGB)
        elif image_input.ndim == 3:
            if image_input.shape[2] == 4:
                img_rgb = cv2.cvtColor(image_input, cv2.COLOR_RGBA2RGB)
            elif image_input.shape[2] == 3:
                img_rgb = image_input.copy()
            elif image_input.shape[0] in (1, 3, 4):
                arr = np.transpose(image_input, (1, 2, 0))
                if arr.shape[2] == 1:
                    img_rgb = cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
                elif arr.shape[2] == 4:
                    img_rgb = cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
                else:
                    img_rgb = arr.copy()
            else:
                raise ValueError(f"Unsupported numpy image shape: {image_input.shape}")
        else:
            raise ValueError(f"Invalid image array dimensions: {image_input.ndim}D")
    else:
        raise TypeError(
            f"Unsupported image_input type '{type(image_input)}'. Expected str, Path, np.ndarray, or PIL.Image."
        )

    if img_rgb.dtype != np.uint8:
        if img_rgb.max() <= 1.0:
            img_rgb = (img_rgb * 255.0).clip(0, 255).astype(np.uint8)
        else:
            img_rgb = img_rgb.clip(0, 255).astype(np.uint8)

    return img_rgb


def preprocess_image(
    image_input: Union[str, Path, np.ndarray, Image.Image],
    target_size: Tuple[int, int] = (config.IMAGE_WIDTH, config.IMAGE_HEIGHT),
) -> Tuple[torch.Tensor, np.ndarray]:
    """Preprocess satellite image for U-Net road segmentation inference.

    Handles file paths, PIL Images, and NumPy arrays.
    Converts Grayscale/RGBA to RGB, resizes to target_size (512, 512),
    normalizes using standard ImageNet parameters, formats to [C, H, W],
    and adds batch dimension -> [1, 3, 512, 512].

    Args:
        image_input (Union[str, Path, np.ndarray, Image.Image]): Raw input image.
        target_size (Tuple[int, int]): Desired (width, height) for model input. Default (512, 512).

    Returns:
        Tuple[torch.Tensor, np.ndarray]:
            - input_tensor: PyTorch tensor of shape (1, 3, H, W) normalized.
            - original_rgb_512: NumPy RGB uint8 array of shape (H, W, 3) for overlay/visualization.
    """
    img_rgb = load_image_raw_rgb(image_input)

    # 2. Resize image to target_size (512, 512)
    target_w, target_h = target_size
    if (img_rgb.shape[1], img_rgb.shape[0]) != (target_w, target_h):
        original_rgb_512 = cv2.resize(img_rgb, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
    else:
        original_rgb_512 = img_rgb.copy()

    # 3. Normalize image: (x / 255.0 - NORM_MEAN) / NORM_STD
    img_float = original_rgb_512.astype(np.float32) / 255.0
    img_normalized = (img_float - NORM_MEAN) / NORM_STD

    # 4. Convert [H, W, C] -> [C, H, W] -> [1, C, H, W] PyTorch Tensor
    tensor_chw = np.transpose(img_normalized, (2, 0, 1))
    input_tensor = torch.from_numpy(tensor_chw).unsqueeze(0).float()

    return input_tensor, original_rgb_512

