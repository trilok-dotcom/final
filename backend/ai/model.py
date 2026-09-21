import os
import sys
from pathlib import Path
from typing import Optional, Union
import torch
import torch.nn as nn
import segmentation_models_pytorch as smp

# Ensure backend directory is in sys.path for standalone module execution
AI_DIR = Path(__file__).resolve().parent
BACKEND_DIR = AI_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def get_default_device() -> torch.device:
    """Automatically detect and return CUDA device if available, else CPU."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


class RoadSegmentationModel(nn.Module):
    """Production-Ready Semantic Segmentation U-Net Neural Network for Disaster Road Mapping.

    Uses U-Net architecture with a ResNet34 encoder pretrained on ImageNet.
    Accepts 3-channel RGB satellite imagery (3, 512, 512) and produces single-channel
    binary road segmentation mask logits (1, 512, 512).
    """

    def __init__(
        self,
        encoder_name: str = "resnet34",
        encoder_weights: Optional[str] = "imagenet",
        in_channels: int = 3,
        classes: int = 1,
        device: Optional[torch.device] = None,
    ) -> None:
        super().__init__()

        self.encoder_name = encoder_name
        self.encoder_weights = encoder_weights
        self.in_channels = in_channels
        self.classes = classes
        self.device = device or get_default_device()

        # Build PyTorch U-Net with ResNet34 encoder via Segmentation Models PyTorch (SMP)
        self.model = smp.Unet(
            encoder_name=self.encoder_name,
            encoder_weights=self.encoder_weights,
            in_channels=self.in_channels,
            classes=self.classes,
            activation=None,  # Output raw logits for numerical stability with BCEWithLogitsLoss
        )

        self.to(self.device)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass of the U-Net segmentation network.

        Args:
            x (torch.Tensor): Input satellite image tensor of shape (B, 3, 512, 512).

        Returns:
            torch.Tensor: Output road mask logits of shape (B, 1, 512, 512).
        """
        # Ensure tensor is on correct device
        if x.device != self.device:
            x = x.to(self.device)
        return self.model(x)

    def predict_mask(
        self, x: torch.Tensor, threshold: float = 0.5
    ) -> torch.Tensor:
        """Inference helper returning binarized probability mask tensor.

        Args:
            x (torch.Tensor): Input image tensor of shape (B, 3, 512, 512).
            threshold (float): Decision threshold for binary segmentation (default 0.5).

        Returns:
            torch.Tensor: Binary mask tensor of shape (B, 1, 512, 512) with values 0.0 or 1.0.
        """
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            probabilities = torch.sigmoid(logits)
            binary_masks = (probabilities > threshold).float()
        return binary_masks

    def save_model(self, file_path: Union[str, Path]) -> None:
        """Save model state_dict checkpoint to disk.

        Args:
            file_path (Union[str, Path]): Destination file path (e.g., 'ai/weights/unet_resnet34.pth').
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "state_dict": self.state_dict(),
                "encoder_name": self.encoder_name,
                "encoder_weights": self.encoder_weights,
                "in_channels": self.in_channels,
                "classes": self.classes,
            },
            str(path),
        )
        print(f"[SUCCESS] Saved RoadSegmentationModel state_dict to '{path}'")

    def load_model(
        self, file_path: Union[str, Path], device: Optional[torch.device] = None
    ) -> None:
        """Load model state_dict checkpoint from disk.

        Args:
            file_path (Union[str, Path]): Checkpoint file path.
            device (Optional[torch.device]): Target device for loading weights.
        """
        target_device = device or self.device
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Model checkpoint not found at '{path}'")

        checkpoint = torch.load(str(path), map_location=target_device)

        if isinstance(checkpoint, dict):
            if "state_dict" in checkpoint:
                self.load_state_dict(checkpoint["state_dict"])
            elif "model_state_dict" in checkpoint:
                self.load_state_dict(checkpoint["model_state_dict"])
            else:
                self.load_state_dict(checkpoint)
        else:
            self.load_state_dict(checkpoint)

        self.to(target_device)
        self.eval()
        print(f"[SUCCESS] Loaded RoadSegmentationModel state_dict from '{path}'")

    def count_parameters(self) -> int:
        """Count total trainable parameters in the model."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


if __name__ == "__main__":
    print("==================================================")
    print("      RESQROUTE AI - U-Net Model Verification     ")
    print("==================================================")

    # 1. Automatically detect device
    device = get_default_device()
    print(f"[INFO] Active PyTorch Device: {device}")

    # 2. Instantiate RoadSegmentationModel with ResNet34 ImageNet encoder
    print("[INFO] Instantiating U-Net (ResNet34 encoder, pretrained='imagenet')...")
    model = RoadSegmentationModel(
        encoder_name="resnet34",
        encoder_weights="imagenet",
        in_channels=3,
        classes=1,
        device=device,
    )

    # 3. Create dummy input tensor: (Batch=1, Channels=3, Height=512, Width=512)
    dummy_input = torch.randn(1, 3, 512, 512).to(device)

    # 4. Perform forward pass
    print("\n--- Forward Pass Execution ---")
    model.eval()
    with torch.no_grad():
        output_logits = model(dummy_input)
        predicted_mask = model.predict_mask(dummy_input, threshold=0.5)

    total_params = model.count_parameters()

    print(f"Input Image Shape : {dummy_input.shape}")
    print(f"Output Logits Shape: {output_logits.shape}")
    print(f"Predicted Mask     : {predicted_mask.shape} (Values: min={predicted_mask.min().item()}, max={predicted_mask.max().item()})")
    print(f"Total Parameters  : {total_params:,} ({total_params / 1e6:.2f} Million)")

    # 5. Verify save_model and load_model helpers
    temp_weights_path = AI_DIR / "weights" / "temp_test_model.pth"
    print(f"\n--- Testing save_model() & load_model() ---")
    model.save_model(temp_weights_path)
    model.load_model(temp_weights_path)

    # Clean up temporary test weights file
    if temp_weights_path.exists():
        temp_weights_path.unlink()
        print("[CLEANUP] Temporary test weights file removed.")

    print("\n==================================================")
    print("     U-Net MODEL MODULE VERIFIED AND READY 100%!   ")
    print("==================================================")
