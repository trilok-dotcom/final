import sys
from pathlib import Path
from typing import Optional, Union, Dict, Any
import numpy as np
import torch
import torch.nn as nn
import segmentation_models_pytorch as smp

# Ensure backend directory is in sys.path
AI_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = AI_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DEFAULT_MODEL_PATH = AI_DIR / "models" / "resqroute_unet_resnet34_v2_best.pth"


def get_inference_device() -> torch.device:
    """Automatically select CUDA GPU if available, else CPU."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


class RoadDetector:
    """Production-ready AI Road Detector for RESQROUTE.

    Loads the trained U-Net + ResNet-34 model once into memory and provides
    fast batch/single-image inference without reloading weights per request.
    """

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        device: Optional[torch.device] = None,
    ) -> None:
        """Initialize and load trained PyTorch U-Net ResNet-34 model.

        Args:
            model_path (Optional[Union[str, Path]]): Path to model checkpoint file (.pth).
            device (Optional[torch.device]): Target torch device ('cuda' or 'cpu').
        """
        self.device = device or get_inference_device()
        self.model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"RESQROUTE model checkpoint not found at '{self.model_path}'. "
                "Ensure resqroute_unet_resnet34_v2_best.pth exists in backend/ai/models/."
            )

        # 1. Instantiate exact U-Net + ResNet-34 architecture used during training
        self.model = smp.Unet(
            encoder_name="resnet34",
            encoder_weights=None,
            in_channels=3,
            classes=1,
            activation=None,  # Outputs raw logits
        )

        # 2. Load checkpoint weights onto target device
        checkpoint = torch.load(str(self.model_path), map_location=self.device)
        if isinstance(checkpoint, dict):
            if "model_state_dict" in checkpoint:
                state_dict = checkpoint["model_state_dict"]
            elif "state_dict" in checkpoint:
                state_dict = checkpoint["state_dict"]
            else:
                state_dict = checkpoint
        else:
            state_dict = checkpoint

        self.model.load_state_dict(state_dict)
        self.model.to(self.device)
        self.model.eval()

        # Optimize for inference
        for param in self.model.parameters():
            param.requires_grad = False

        print(f"[INFO] RoadDetector initialized on '{self.device}' using model: '{self.model_path.name}'")

    @torch.no_grad()
    def predict_probability(self, input_tensor: torch.Tensor) -> np.ndarray:
        """Run image tensor through U-Net model and compute probability map.

        Args:
            input_tensor (torch.Tensor): Preprocessed input image tensor of shape (1, 3, 512, 512).

        Returns:
            np.ndarray: 2D probability map array of shape (512, 512) with values in range [0.0, 1.0].
        """
        if not isinstance(input_tensor, torch.Tensor):
            raise TypeError(f"Expected input_tensor to be a PyTorch Tensor, got {type(input_tensor)}")

        if input_tensor.ndim == 3:
            input_tensor = input_tensor.unsqueeze(0)

        if input_tensor.shape[1] != 3 or input_tensor.shape[2] != 512 or input_tensor.shape[3] != 512:
            raise ValueError(
                f"Expected tensor shape (1, 3, 512, 512) or (3, 512, 512), got {input_tensor.shape}"
            )

        input_tensor = input_tensor.to(self.device, non_blocking=True)

        logits = self.model(input_tensor)
        probabilities = torch.sigmoid(logits)

        # Remove batch and channel dimensions -> (512, 512) numpy float32
        prob_map = probabilities.squeeze().detach().cpu().numpy().astype(np.float32)
        return prob_map
