from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
import cv2
import numpy as np
import networkx as nx
from PIL import Image, ImageDraw

# ============================================================
# RESQROUTE AI - SIMPLIFIED ROAD GRAPH & ROUTE GENERATION
# ============================================================

AI_DIR = Path(__file__).resolve().parent

SKELETON_PATH = (
    AI_DIR
    / "outputs"
    / "road_network"
    / "road_skeleton.png"
)

PREDICTION_MASK_PATH = (
    AI_DIR
    / "outputs"
    / "prediction_mask.png"
)

ORIGINAL_IMAGE_PATH = (
    AI_DIR
    / "datasets"
    / "test"
    / "100703_sat.jpg"
)

OUTPUT_DIR = (
    AI_DIR
    / "outputs"
    / "route"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Configurable Parameters
MIN_BRANCH_LENGTH = 15           # Prune dead-end spur branches shorter than this pixel length
MAX_SNAP_DISTANCE_PIXELS = 120.0 # Maximum allowed snapping distance from target pixel to road network
CONFIDENCE_PENALTY_WEIGHT = 1.5  # Weight factor penalizing low confidence road predictions
DOUGLAS_PEUCKER_EPSILON = 2.5   # Line simplification tolerance in pixels

# 8-connected neighbourhood offsets
NEIGHBOURS = [
    (-1, -1), (0, -1), (1, -1),
    (-1,  0),          (1,  0),
    (-1,  1), (0,  1), (1,  1),
]

# In-Memory Cache for Instantaneous Live Demo Responses
_GRAPH_CACHE: Optional[nx.Graph] = None
_CACHED_SKELETON_PATH: Optional[str] = None


def _euclidean_dist(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate Euclidean distance between two 2D points."""
    return float(np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2))


def build_simplified_road_graph(
    skeleton_image: np.ndarray,
    prob_mask: Optional[np.ndarray] = None,
    min_branch_length: int = MIN_BRANCH_LENGTH,
    confidence_penalty: float = CONFIDENCE_PENALTY_WEIGHT,
) -> nx.Graph:
    """Build a simplified NetworkX road graph from 1-pixel skeleton image.

    Nodes represent junctions (degree >= 3) and endpoints (degree 1).
    Edges represent whole road segments connecting junctions and endpoints.

    Args:
        skeleton_image (np.ndarray): 2D binary uint8 skeleton image (0 or 255).
        prob_mask (Optional[np.ndarray]): Probability mask for confidence weighting.
        min_branch_length (int): Prune dead-end spur branches shorter than this length.
        confidence_penalty (float): Penalty multiplier for lower confidence predictions.

    Returns:
        nx.Graph: Simplified NetworkX road graph.
    """
    skel_bool = skeleton_image > 0
    height, width = skel_bool.shape

    ys, xs = np.where(skel_bool)
    if len(xs) < 10:
        raise RuntimeError("Not enough road skeleton pixels to build graph.")

    skel_set = set(zip(xs, ys))

    # 1. Degree calculation for each skeleton pixel
    degree_map: Dict[Tuple[int, int], int] = {}
    neighbors_map: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}

    for x, y in skel_set:
        nbrs = []
        for dx, dy in NEIGHBOURS:
            nx_pos, ny_pos = x + dx, y + dy
            if (nx_pos, ny_pos) in skel_set:
                nbrs.append((nx_pos, ny_pos))
        degree_map[(x, y)] = len(nbrs)
        neighbors_map[(x, y)] = nbrs

    # 2. Identify Junction Pixels (degree >= 3) and Endpoints (degree == 1)
    junction_pixels = {p for p, deg in degree_map.items() if deg >= 3}
    endpoint_pixels = {p for p, deg in degree_map.items() if deg == 1}

    # 3. Cluster adjacent Junction Pixels into single Junction Nodes
    junction_mask = np.zeros((height, width), dtype=np.uint8)
    for jx, jy in junction_pixels:
        junction_mask[jy, jx] = 255

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(junction_mask, connectivity=8)

    pixel_to_keynode: Dict[Tuple[int, int], Tuple[int, int]] = {}
    keynode_to_pixels: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}

    for label_idx in range(1, num_labels):
        comp_ys, comp_xs = np.where(labels == label_idx)
        comp_pixels = list(zip(comp_xs, comp_ys))
        
        # Centroid mapped to nearest pixel in component
        cx_mean = float(np.mean(comp_xs))
        cy_mean = float(np.mean(comp_ys))
        best_pixel = min(comp_pixels, key=lambda p: (p[0] - cx_mean) ** 2 + (p[1] - cy_mean) ** 2)
        
        for p in comp_pixels:
            pixel_to_keynode[p] = best_pixel
        keynode_to_pixels[best_pixel] = comp_pixels

    # Endpoints map to themselves
    for ep in endpoint_pixels:
        if ep not in pixel_to_keynode:
            pixel_to_keynode[ep] = ep
            keynode_to_pixels[ep] = [ep]

    # Handle isolated loops/components without junctions or endpoints (degree == 2 everywhere)
    visited_pixels = set()
    for p in skel_set:
        if p not in pixel_to_keynode and degree_map.get(p, 0) == 2:
            # Check if this pixel is part of a loop
            loop_pixels = []
            curr = p
            prev = None
            is_closed_loop = True
            while curr not in loop_pixels:
                loop_pixels.append(curr)
                nbrs = neighbors_map[curr]
                next_p = None
                for n in nbrs:
                    if n != prev:
                        next_p = n
                        break
                if next_p is None:
                    is_closed_loop = False
                    break
                prev = curr
                curr = next_p
                if curr in pixel_to_keynode:
                    is_closed_loop = False
                    break
            
            if is_closed_loop and len(loop_pixels) > 0:
                key_p = loop_pixels[0]
                for lp in loop_pixels:
                    pixel_to_keynode[lp] = key_p
                keynode_to_pixels[key_p] = loop_pixels

    # 4. Trace Road Segments between Key Nodes
    G = nx.Graph()

    # Add all key nodes to graph
    for key_node in keynode_to_pixels.keys():
        G.add_node(key_node, pos=key_node)

    traced_edges = set()

    for start_pixel in skel_set:
        if start_pixel in pixel_to_keynode:
            start_key = pixel_to_keynode[start_pixel]
            # Explore all neighbors
            for nbr in neighbors_map[start_pixel]:
                if nbr in pixel_to_keynode and pixel_to_keynode[nbr] == start_key:
                    continue  # Internal pixel inside same junction cluster

                edge_key = tuple(sorted([start_pixel, nbr]))
                if edge_key in traced_edges:
                    continue
                traced_edges.add(edge_key)

                # Trace along corridor (degree 2 pixels) until hitting a keynode pixel
                path_pixels = [start_pixel, nbr]
                curr = nbr
                prev = start_pixel

                while curr not in pixel_to_keynode:
                    nbrs = neighbors_map[curr]
                    next_step = None
                    for n in nbrs:
                        if n != prev:
                            next_step = n
                            break
                    if next_step is None:
                        break
                    path_pixels.append(next_step)
                    prev = curr
                    curr = next_step

                if curr in pixel_to_keynode:
                    end_key = pixel_to_keynode[curr]

                    # Full pixel polyline from start_key to end_key
                    full_pixels = [start_key] + path_pixels + [end_key]
                    # Deduplicate adjacent duplicate coordinates
                    clean_pixels = []
                    for pt in full_pixels:
                        if not clean_pixels or clean_pixels[-1] != pt:
                            clean_pixels.append(pt)

                    # Compute spatial length along segment
                    seg_len = 0.0
                    for i in range(len(clean_pixels) - 1):
                        seg_len += _euclidean_dist(clean_pixels[i], clean_pixels[i + 1])

                    # Compute average road probability / confidence
                    if prob_mask is not None:
                        prob_vals = []
                        for px, py in clean_pixels:
                            if 0 <= py < height and 0 <= px < width:
                                val = prob_mask[py, px]
                                prob_vals.append(val if val <= 1.0 else val / 255.0)
                        avg_conf = float(np.mean(prob_vals)) if prob_vals else 0.8
                    else:
                        avg_conf = 0.9

                    # Calculate weighted cost
                    weight_cost = seg_len * (1.0 + confidence_penalty * (1.0 - avg_conf))

                    if start_key != end_key or len(clean_pixels) > 2:
                        if G.has_edge(start_key, end_key):
                            existing_weight = G[start_key][end_key]["weight"]
                            if weight_cost < existing_weight:
                                G.add_edge(
                                    start_key,
                                    end_key,
                                    weight=weight_cost,
                                    pixels=clean_pixels,
                                    length=seg_len,
                                    confidence=avg_conf,
                                )
                        else:
                            G.add_edge(
                                start_key,
                                end_key,
                                weight=weight_cost,
                                pixels=clean_pixels,
                                length=seg_len,
                                confidence=avg_conf,
                            )

    # 5. Prune Spurious Dead-End Branches (< MIN_BRANCH_LENGTH)
    G = prune_spurious_branches(G, min_branch_length=min_branch_length)

    return G


def prune_spurious_branches(G: nx.Graph, min_branch_length: int = MIN_BRANCH_LENGTH) -> nx.Graph:
    """Iteratively remove short dead-end spur branches attached to junctions.

    Args:
        G (nx.Graph): Road network graph.
        min_branch_length (int): Threshold branch length in pixels.

    Returns:
        nx.Graph: Pruned road graph.
    """
    G_pruned = G.copy()
    changed = True

    while changed:
        changed = False
        dead_ends = [node for node, deg in G_pruned.degree() if deg == 1]

        for node in dead_ends:
            if not G_pruned.has_node(node):
                continue
            nbr = list(G_pruned.neighbors(node))[0]
            edge_data = G_pruned.get_edge_data(node, nbr)
            seg_len = edge_data.get("length", 0.0)

            # If dead-end branch is shorter than threshold, remove it
            if seg_len < min_branch_length:
                G_pruned.remove_node(node)
                changed = True

    return G_pruned


def snap_pixel_to_road_graph(
    graph: nx.Graph,
    target_pixel: Tuple[int, int],
    max_distance: float = MAX_SNAP_DISTANCE_PIXELS,
) -> Tuple[Optional[Tuple[int, int]], float, Optional[Tuple[Any, Any]], int]:
    """Snap a target (x, y) pixel coordinate to the nearest road segment or node in graph.

    Args:
        graph (nx.Graph): Simplified road graph.
        target_pixel (Tuple[int, int]): Target (x, y) coordinate.
        max_distance (float): Maximum allowable distance in pixels.

    Returns:
        Tuple: (snapped_point, min_distance, edge_nodes_tuple, edge_segment_index)
    """
    tx, ty = target_pixel
    min_dist = float("inf")
    best_snap = None
    best_edge = None
    best_idx = 0

    for u, v, data in graph.edges(data=True):
        pixels = data.get("pixels", [u, v])
        for idx in range(len(pixels)):
            px, py = pixels[idx]
            dist = _euclidean_dist((tx, ty), (px, py))
            if dist < min_dist:
                min_dist = dist
                best_snap = (int(px), int(py))
                best_edge = (u, v)
                best_idx = idx

    is_valid = min_dist <= max_distance
    if not is_valid:
        return None, min_dist, None, 0

    return best_snap, min_dist, best_edge, best_idx


def smooth_route_geometry(path_pixels: List[Tuple[int, int]], epsilon: float = DOUGLAS_PEUCKER_EPSILON) -> List[Tuple[int, int]]:
    """Simplify route polyline using Douglas-Peucker algorithm (cv2.approxPolyDP).

    Args:
        path_pixels (List[Tuple[int, int]]): Full pixel path.
        epsilon (float): Douglas-Peucker approximation accuracy parameter.

    Returns:
        List[Tuple[int, int]]: Simplified route waypoints.
    """
    if len(path_pixels) <= 2:
        return path_pixels

    pts = np.array(path_pixels, dtype=np.int32).reshape((-1, 1, 2))
    simplified = cv2.approxPolyDP(pts, epsilon=epsilon, closed=False)
    smoothed = [tuple(p[0]) for p in simplified]

    # Ensure start and end points remain exact
    if smoothed[0] != path_pixels[0]:
        smoothed[0] = path_pixels[0]
    if smoothed[-1] != path_pixels[-1]:
        smoothed[-1] = path_pixels[-1]

    return smoothed


def calculate_route(
    graph: nx.Graph,
    start_pixel: Tuple[int, int],
    dest_pixel: Tuple[int, int],
    max_distance: float = MAX_SNAP_DISTANCE_PIXELS,
    douglas_peucker_epsilon: float = DOUGLAS_PEUCKER_EPSILON,
) -> Dict[str, Any]:
    """Calculate shortest weighted route on simplified graph between start and destination pixels.

    Args:
        graph (nx.Graph): Simplified road graph.
        start_pixel (Tuple[int, int]): Start (x, y) coordinate.
        dest_pixel (Tuple[int, int]): Destination (x, y) coordinate.
        max_distance (float): Max distance to snap to road graph.
        douglas_peucker_epsilon (float): Line simplification tolerance.

    Returns:
        Dict[str, Any]: Route result dictionary.
    """
    # 1. Snap start location
    start_snap, start_dist, start_edge, start_idx = snap_pixel_to_road_graph(graph, start_pixel, max_distance)
    if start_snap is None:
        raise ValueError(
            f"Selected start location is too far ({start_dist:.1f}px) from the detected road network."
        )

    # 2. Snap destination location
    dest_snap, dest_dist, dest_edge, dest_idx = snap_pixel_to_road_graph(graph, dest_pixel, max_distance)
    if dest_snap is None:
        raise ValueError(
            f"Selected destination location is too far ({dest_dist:.1f}px) from the detected road network."
        )

    # 3. Create a temporary working copy of graph and inject start/dest snap nodes
    work_G = graph.copy()

    def _inject_node_on_edge(G: nx.Graph, snap_pt: Tuple[int, int], edge: Tuple[Any, Any], idx: int):
        u, v = edge
        if not G.has_edge(u, v):
            return snap_pt
        data = G[u][v]
        pixels = list(data.get("pixels", [u, v]))

        if snap_pt == u or snap_pt == v:
            return snap_pt

        # Ensure pixels array starts at u and ends at v
        if len(pixels) >= 2 and pixels[0] != u:
            pixels = list(reversed(pixels))
            idx = len(pixels) - 1 - idx

        G.remove_edge(u, v)
        sub1_pixels = pixels[: idx + 1]
        sub2_pixels = pixels[idx:]

        len1 = sum(_euclidean_dist(sub1_pixels[i], sub1_pixels[i + 1]) for i in range(len(sub1_pixels) - 1))
        len2 = sum(_euclidean_dist(sub2_pixels[i], sub2_pixels[i + 1]) for i in range(len(sub2_pixels) - 1))
        conf = data.get("confidence", 0.8)

        w1 = len1 * (1.0 + CONFIDENCE_PENALTY_WEIGHT * (1.0 - conf))
        w2 = len2 * (1.0 + CONFIDENCE_PENALTY_WEIGHT * (1.0 - conf))

        G.add_edge(u, snap_pt, weight=w1, pixels=sub1_pixels, length=len1, confidence=conf)
        G.add_edge(snap_pt, v, weight=w2, pixels=sub2_pixels, length=len2, confidence=conf)
        return snap_pt

    actual_start_node = _inject_node_on_edge(work_G, start_snap, start_edge, start_idx) if start_edge else start_snap
    actual_dest_node = _inject_node_on_edge(work_G, dest_snap, dest_edge, dest_idx) if dest_edge else dest_snap

    # 4. A* Shortest Path Search
    def heuristic(u, v):
        return _euclidean_dist(u, v)

    try:
        path_nodes = nx.astar_path(work_G, source=actual_start_node, target=actual_dest_node, heuristic=heuristic, weight="weight")
    except nx.NetworkXNoPath:
        raise RuntimeError("No connected AI-detected road route exists between the selected locations.")

    # 5. Reconstruct Raw Pixel Path
    raw_path: List[Tuple[int, int]] = []
    total_length = 0.0

    for i in range(len(path_nodes) - 1):
        n1 = path_nodes[i]
        n2 = path_nodes[i + 1]
        edge_data = work_G[n1][n2]
        seg_pixels = list(edge_data.get("pixels", [n1, n2]))
        total_length += edge_data.get("length", 0.0)

        if seg_pixels[0] != n1:
            seg_pixels = list(reversed(seg_pixels))

        for pt in seg_pixels:
            if not raw_path or raw_path[-1] != pt:
                raw_path.append(pt)

    # Force exact start and end node endpoints
    if raw_path[0] != actual_start_node:
        raw_path.insert(0, actual_start_node)
    if raw_path[-1] != actual_dest_node:
        raw_path.append(actual_dest_node)

    # 6. Apply Douglas-Peucker Route Smoothing
    smoothed_path = smooth_route_geometry(raw_path, epsilon=douglas_peucker_epsilon)
    if smoothed_path[0] != actual_start_node:
        smoothed_path[0] = actual_start_node
    if smoothed_path[-1] != actual_dest_node:
        smoothed_path[-1] = actual_dest_node

    return {
        "path": smoothed_path,
        "raw_path": raw_path,
        "route_length_pixels": total_length,
        "start_node": actual_start_node,
        "end_node": actual_dest_node,
        "start_snap_dist": start_dist,
        "end_snap_dist": dest_dist,
    }


def get_or_build_road_graph(
    skeleton_path: Optional[Path] = None,
    prob_path: Optional[Path] = None,
    force_rebuild: bool = False,
) -> nx.Graph:
    """Retrieve or build cached simplified NetworkX graph for live demo response."""
    global _GRAPH_CACHE, _CACHED_SKELETON_PATH

    skel_file = Path(skeleton_path) if skeleton_path else SKELETON_PATH

    if not force_rebuild and _GRAPH_CACHE is not None and _CACHED_SKELETON_PATH == str(skel_file):
        return _GRAPH_CACHE

    if not skel_file.exists():
        from ai.road_network import process_road_network
        process_road_network()

    skeleton_img = cv2.imread(str(skel_file), cv2.IMREAD_GRAYSCALE)
    if skeleton_img is None:
        raise FileNotFoundError(f"Failed to read skeleton image at '{skel_file}'")

    pr_file = Path(prob_path) if prob_path else PREDICTION_MASK_PATH
    prob_img = None
    if pr_file.exists():
        prob_img = cv2.imread(str(pr_file), cv2.IMREAD_GRAYSCALE)

    _GRAPH_CACHE = build_simplified_road_graph(skeleton_img, prob_mask=prob_img)
    _CACHED_SKELETON_PATH = str(skel_file)
    return _GRAPH_CACHE


def generate_route_visualizations(
    graph: nx.Graph,
    path: List[Tuple[int, int]],
    start_node: Tuple[int, int],
    end_node: Tuple[int, int],
    bg_image_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    width: int = 512,
    height: int = 512,
) -> Dict[str, str]:
    """Generate debug visualizations: road_graph.png and route_debug.png."""
    out_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    img_file = Path(bg_image_path) if bg_image_path else ORIGINAL_IMAGE_PATH

    if img_file.exists():
        base_img = Image.open(img_file).convert("RGB").resize((width, height))
    else:
        base_img = Image.new("RGB", (width, height), (30, 30, 30))

    # A. Save road_graph.png (showing graph nodes, edges, junctions, endpoints)
    graph_img = base_img.copy()
    g_draw = ImageDraw.Draw(graph_img)

    for u, v, data in graph.edges(data=True):
        pixels = data.get("pixels", [u, v])
        for i in range(len(pixels) - 1):
            g_draw.line([pixels[i], pixels[i + 1]], fill=(0, 220, 255), width=2)

    for node, deg in graph.degree():
        nx_p, ny_p = node
        if deg >= 3:
            # Junction Node (ORANGE)
            g_draw.ellipse([nx_p - 4, ny_p - 4, nx_p + 4, ny_p + 4], fill=(255, 140, 0), outline=(255, 255, 255), width=1)
        elif deg == 1:
            # Endpoint Node (CYAN)
            g_draw.ellipse([nx_p - 3, ny_p - 3, nx_p + 3, ny_p + 3], fill=(0, 255, 255), outline=(0, 0, 0), width=1)

    graph_debug_path = out_dir / "road_graph.png"
    graph_img.save(graph_debug_path)

    # B. Save route_debug.png (showing sat image, extracted roads, start, dest, final route)
    route_img = base_img.copy()
    r_draw = ImageDraw.Draw(route_img)

    # Draw Extracted Road Network in Gray
    for u, v, data in graph.edges(data=True):
        pixels = data.get("pixels", [u, v])
        for i in range(len(pixels) - 1):
            r_draw.line([pixels[i], pixels[i + 1]], fill=(180, 180, 180), width=2)

    # Draw Final Rescue Route in Thick RED Line
    for i in range(len(path) - 1):
        x1, y1 = path[i]
        x2, y2 = path[i + 1]
        r_draw.line([(x1, y1), (x2, y2)], fill=(255, 0, 0), width=5)

    # Draw Green Start Marker (GREEN 🟢)
    sx, sy = start_node
    r_draw.ellipse([sx - 7, sy - 7, sx + 7, sy + 7], fill=(0, 255, 0), outline=(255, 255, 255), width=2)

    # Draw Blue Destination Marker (BLUE 🔵)
    ex, ey = end_node
    r_draw.ellipse([ex - 7, ey - 7, ex + 7, ey + 7], fill=(0, 120, 255), outline=(255, 255, 255), width=2)

    route_debug_path = out_dir / "route_debug.png"
    route_img.save(route_debug_path)

    rescue_route_path = out_dir / "rescue_route.png"
    route_img.save(rescue_route_path)

    return {
        "road_graph.png": str(graph_debug_path),
        "route_debug.png": str(route_debug_path),
        "rescue_route.png": str(rescue_route_path),
    }


if __name__ == "__main__":
    print("=" * 60)
    print("       RESQROUTE AI - ROAD ROUTE GENERATION")
    print("=" * 60)

    graph = get_or_build_road_graph()
    print(f"[SUCCESS] Simplified Graph loaded! Nodes: {graph.number_of_nodes()}, Edges: {graph.number_of_edges()}")

    # Example test route calculation using georeferenced coordinates
    from ai.georeference import georeference
    req_start_lat, req_start_lon = 12.9640, 77.5900
    req_dest_lat, req_dest_lon = 12.9750, 77.5920

    start_target = georeference.geo_to_pixel(req_start_lat, req_start_lon)
    end_target = georeference.geo_to_pixel(req_dest_lat, req_dest_lon)

    print(f"[INFO] Calculating route from Geo ({req_start_lat}, {req_start_lon}) [Pixel {start_target}] to Geo ({req_dest_lat}, {req_dest_lon}) [Pixel {end_target}]...")
    res = calculate_route(graph, start_target, end_target)

    path = res["path"]
    length = res["route_length_pixels"]
    print(f"[SUCCESS] Route calculated! Waypoints: {len(path)}, Length: {length:.2f} px")

    vis = generate_route_visualizations(graph, path, res["start_node"], res["end_node"])
    print(f"[SUCCESS] Debug visualizations saved:")
    print(f"  - Road Graph  : {vis['road_graph.png']}")
    print(f"  - Route Debug : {vis['route_debug.png']}")
    print("=" * 60)