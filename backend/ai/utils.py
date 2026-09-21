from typing import List, Tuple, Dict, Any
import cv2
import numpy as np
import networkx as nx
from app.utils.logging import get_logger

logger = get_logger("ai.utils")


def preprocess_satellite_image(
    image_bytes: bytes, target_size: Tuple[int, int] = (512, 512)
) -> np.ndarray:
    """Decode raw image bytes into normalized OpenCV array suitable for PyTorch tensor input."""
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes.")
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(img_rgb, target_size)
    return resized.astype(np.float32) / 255.0


def extract_road_network_graph(mask: np.ndarray) -> nx.Graph:
    """Build NetworkX Graph from binary road segmentation mask.

    Each node represents a road intersection/waypoint, and each edge represents a road segment
    weighted by distance and damage condition.
    """
    logger.info("Extracting NetworkX road network graph from prediction mask...")
    G = nx.Graph()

    # Stub graph generation for demonstration & future Dijkstra integration
    # Create nodes
    nodes = [
        (0, {"pos": (12.9716, 77.5946), "label": "Start Point"}),
        (1, {"pos": (12.9750, 77.5980), "label": "Intersection A"}),
        (2, {"pos": (12.9780, 77.6010), "label": "Intersection B"}),
        (3, {"pos": (12.9820, 77.6050), "label": "Destination"}),
    ]

    for node_id, data in nodes:
        G.add_node(node_id, **data)

    # Add edges with weights (distance in km, status, damage factor)
    G.add_edge(0, 1, weight=1.2, status="safe", damage_factor=1.0)
    G.add_edge(1, 2, weight=2.1, status="damaged", damage_factor=1.5)
    G.add_edge(2, 3, weight=1.8, status="safe", damage_factor=1.0)
    G.add_edge(1, 3, weight=5.0, status="blocked", damage_factor=999.0)

    return G
