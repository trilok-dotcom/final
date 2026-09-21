"""AI Engine Package for RESQROUTE AI.

Contains PyTorch U-Net neural network architecture, dataset loader, training script,
inference predictor service, and OpenCV/NetworkX postprocessing utilities.
"""
try:
    from .predict import UNetPredictor
except ImportError:
    from ai.predict import UNetPredictor

__all__ = ["UNetPredictor"]

