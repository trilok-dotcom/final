import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import cv2
import numpy as np
import networkx as nx
from skimage.morphology import skeletonize

AI_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = AI_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Default validated decision threshold for V2 model
DEFAULT_THRESHOLD = 0.25


def postprocess_mask(
    prob_map: np.ndarray,
    threshold: float = DEFAULT_THRESHOLD,
    min_component_size: int = 50,
    morph_kernel_size: int = 3,
    close_iterations: int = 1,
    open_iterations: int = 0,
) -> np.ndarray:
    """Create clean binary road mask from model probability map.

    Applies probability thresholding (default 0.25), morphological closing
    to bridge minor road breaks, and component filtering to remove small noise.

    Args:
        prob_map (np.ndarray): 2D probability map array [512, 512] with values in range [0, 1].
        threshold (float): Decision threshold. Default 0.25 (validated for V2 model).
        min_component_size (int): Minimum pixel area for connected component to keep. Default 50.
        morph_kernel_size (int): Structuring element kernel size for morphological operations. Default 3.
        close_iterations (int): Iterations of cv2.MORPH_CLOSE to connect road gaps. Default 1.
        open_iterations (int): Iterations of cv2.MORPH_OPEN to remove background specs. Default 0.

    Returns:
        np.ndarray: Binary mask array of shape [512, 512] with uint8 values 0 or 255.
    """
    if prob_map.ndim != 2:
        raise ValueError(f"Expected 2D probability map array, got {prob_map.ndim}D")

    # 1. Binarize with validated threshold (0.25)
    binary = (prob_map >= threshold).astype(np.uint8) * 255

    # 2. Morphological Operations (bridge minor gaps while preserving thin roads)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (morph_kernel_size, morph_kernel_size))
    
    if close_iterations > 0:
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=close_iterations)

    if open_iterations > 0:
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=open_iterations)

    # 3. Connected Component Filtering (remove small isolated noise specs)
    if min_component_size > 0:
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        cleaned = np.zeros_like(binary)
        for i in range(1, num_labels):
            if stats[i, cv2.CC_STAT_AREA] >= min_component_size:
                cleaned[labels == i] = 255
        return cleaned

    return binary


def create_road_overlay(
    image: np.ndarray,
    mask: np.ndarray,
    alpha: float = 0.4,
    color: Tuple[int, int, int] = (0, 255, 255),
) -> np.ndarray:
    """Create a semi-transparent road mask overlay on top of original satellite image.

    Args:
        image (np.ndarray): Original satellite RGB image uint8 array of shape [512, 512, 3].
        mask (np.ndarray): Binary road mask uint8 array of shape [512, 512] (0 or 255).
        alpha (float): Transparency blending weight for mask (0.0 to 1.0). Default 0.4.
        color (Tuple[int, int, int]): Overlay color in RGB format. Default Cyan (0, 255, 255).

    Returns:
        np.ndarray: Blended RGB uint8 image array of shape [512, 512, 3].
    """
    if image.shape[:2] != mask.shape[:2]:
        raise ValueError(f"Image shape {image.shape} and mask shape {mask.shape} dimensions do not match")

    if image.ndim == 2:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    else:
        image_rgb = image.copy()

    overlay = image_rgb.copy()
    road_indices = mask > 0

    # Colorize road mask pixels
    color_arr = np.array(color, dtype=np.uint8)
    colored_mask = np.zeros_like(image_rgb)
    colored_mask[road_indices] = color_arr

    # Blend original image and colored mask where mask > 0
    blended = image_rgb.astype(np.float32)
    blended[road_indices] = (
        (1.0 - alpha) * image_rgb[road_indices].astype(np.float32)
        + alpha * color_arr.astype(np.float32)
    )

    return np.clip(blended, 0, 255).astype(np.uint8)


def extract_road_network(
    mask: np.ndarray,
    prob_map: Optional[np.ndarray] = None,
    min_branch_length: int = 10,
) -> Dict[str, Any]:
    """Convert binary road mask into graph representation of road network for routing.

    Steps:
    1. Skeletonize binary road mask to 1-pixel centerlines
    2. Identify key topological nodes (junctions degree >= 3 and endpoints degree == 1)
    3. Trace road segment edges between nodes
    4. Construct NetworkX graph with node positions, segment geometries, and lengths

    Args:
        mask (np.ndarray): Binary uint8 road mask [512, 512] (0 or 255).
        prob_map (Optional[np.ndarray]): Optional 2D float probability map for weighting.
        min_branch_length (int): Prune short spur branches under this pixel length. Default 10.

    Returns:
        Dict[str, Any]:
            - graph: networkx.Graph object
            - nodes: list of dicts with node id and (x, y) coordinates
            - edges: list of dicts with source, target, distance, geometry points
            - skeleton: 2D uint8 array [512, 512] of 1-pixel thinned road network
    """
    # 1. Skeletonize mask to 1-pixel centerlines
    binary_bool = mask > 0
    if not np.any(binary_bool):
        # Empty mask
        empty_graph = nx.Graph()
        return {
            "graph": empty_graph,
            "nodes": [],
            "edges": [],
            "skeleton": np.zeros_like(mask, dtype=np.uint8),
        }

    skel_bool = skeletonize(binary_bool)
    skeleton = (skel_bool.astype(np.uint8)) * 255

    # 2. Extract skeleton coordinates and build pixel graph
    height, width = skeleton.shape
    skel_pts = np.argwhere(skel_bool)  # rows (y), cols (x)

    # 8-connectivity offset vectors
    neighbors_offset = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),          (0, 1),
        (1, -1),  (1, 0),  (1, 1),
    ]

    # Map (y, x) -> degree
    deg_map: Dict[Tuple[int, int], int] = {}
    pt_set = set(map(tuple, skel_pts))

    for y, x in pt_set:
        deg = 0
        for dy, dx in neighbors_offset:
            if (y + dy, x + dx) in pt_set:
                deg += 1
        deg_map[(y, x)] = deg

    # Key nodes: endpoints (deg == 1) and junctions (deg >= 3)
    # Also handle isolated loops (deg == 2 everywhere)
    key_nodes = {pt for pt, deg in deg_map.items() if deg != 2}
    if not key_nodes and pt_set:
        # Fallback if ring/loop with no endpoints/junctions
        key_nodes = {next(iter(pt_set))}

    # Assign integer IDs to key nodes
    node_id_map: Dict[Tuple[int, int], int] = {pt: i for i, pt in enumerate(sorted(key_nodes))}

    graph = nx.Graph()
    for pt, node_id in node_id_map.items():
        # Store as (x, y) coordinate standard for GIS / plotting
        graph.add_node(node_id, pos=(pt[1], pt[0]), y=pt[0], x=pt[1])

    # 3. Trace segments between key nodes
    visited_edges = set()

    for start_pt in key_nodes:
        # Explore neighbors
        for dy, dx in neighbors_offset:
            neighbor = (start_pt[0] + dy, start_pt[1] + dx)
            if neighbor in pt_set:
                # Trace path until another key node is reached
                curr = neighbor
                prev = start_pt
                path_pts = [start_pt, curr]

                while curr not in key_nodes:
                    next_pts = []
                    for ndy, ndx in neighbors_offset:
                        nxt = (curr[0] + ndy, curr[1] + ndx)
                        if nxt in pt_set and nxt != prev:
                            next_pts.append(nxt)

                    if not next_pts:
                        break
                    prev = curr
                    curr = next_pts[0]
                    path_pts.append(curr)

                if curr in key_nodes and curr != start_pt:
                    u = node_id_map[start_pt]
                    v = node_id_map[curr]
                    edge_key = tuple(sorted((u, v)))

                    if edge_key not in visited_edges:
                        visited_edges.add(edge_key)

                        # Calculate Euclidean distance along line segment
                        dist = 0.0
                        for k in range(len(path_pts) - 1):
                            p1, p2 = path_pts[k], path_pts[k + 1]
                            dist += float(np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2))

                        # Average confidence score along segment if prob_map is available
                        if prob_map is not None:
                            probs = [prob_map[py, px] for py, px in path_pts]
                            avg_conf = float(np.mean(probs))
                        else:
                            avg_conf = 1.0

                        # Convert path points to [(x, y), ...]
                        geom_xy = [(px, py) for py, px in path_pts]

                        graph.add_edge(
                            u, v,
                            weight=dist,
                            length=dist,
                            confidence=avg_conf,
                            geometry=geom_xy,
                        )

    # 4. Optional: Prune short dead-end spur branches
    if min_branch_length > 0:
        dead_ends = [n for n in graph.nodes if graph.degree(n) == 1]
        for n in dead_ends:
            if graph.degree(n) == 1:
                neighbor = next(graph.neighbors(n))
                edge_data = graph.get_edge_data(n, neighbor)
                if edge_data and edge_data.get("length", 0) < min_branch_length:
                    graph.remove_node(n)

    # Prepare structured summary dict
    nodes_list = [
        {"id": n, "x": data["x"], "y": data["y"], "pos": data["pos"]}
        for n, data in graph.nodes(data=True)
    ]
    edges_list = [
        {
            "source": u,
            "target": v,
            "weight": round(data.get("weight", 0.0), 2),
            "length": round(data.get("length", 0.0), 2),
            "confidence": round(data.get("confidence", 1.0), 4),
            "points": data.get("geometry", []),
        }
        for u, v, data in graph.edges(data=True)
    ]

    return {
        "graph": graph,
        "nodes": nodes_list,
        "edges": edges_list,
        "skeleton": skeleton,
    }
