import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Union, Set
import cv2
import numpy as np
import networkx as nx
from PIL import Image, ImageDraw, ImageFont
from skimage.morphology import skeletonize

from app.utils.logging import get_logger

logger = get_logger("road_network_service")

# Default Parameters for Light Morphological Cleaning
ROAD_THRESHOLD = 0.40
MIN_COMPONENT_SIZE = 30
MORPH_KERNEL_SIZE = 3

NEIGHBORS = [
    (-1, -1), (0, -1), (1, -1),
    (-1,  0),          (1,  0),
    (-1,  1), (0,  1), (1,  1),
]


class RoadNetworkService:
    """Service to clean AI prediction mask, skeletonize roads, extract NetworkX graph,
    and export GeoJSON & debug visual overlays.
    """

    def clean_road_mask(
        self,
        mask_input: np.ndarray,
        threshold: float = ROAD_THRESHOLD,
        min_component_size: int = MIN_COMPONENT_SIZE,
    ) -> np.ndarray:
        """Apply light morphological cleanup to fill tiny road gaps and remove background noise."""
        if mask_input.dtype in (np.float32, np.float64):
            binary = (mask_input >= threshold).astype(np.uint8) * 255
        else:
            thresh_val = int(threshold * 255) if threshold <= 1.0 else int(threshold)
            binary = np.zeros_like(mask_input, dtype=np.uint8)
            binary[mask_input >= thresh_val] = 255

        # Light Morphological Closing to bridge narrow gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (MORPH_KERNEL_SIZE, MORPH_KERNEL_SIZE))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

        # Light Morphological Opening to remove minor isolated specs
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel, iterations=1)

        # Connected component filtering to eliminate tiny disconnected noise specs
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)
        cleaned = np.zeros_like(opened)

        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area >= min_component_size:
                cleaned[labels == i] = 255

        return cleaned

    def extract_skeleton(self, cleaned_mask: np.ndarray) -> np.ndarray:
        """Skeletonize binary road mask to 1-pixel thin centerlines."""
        skel_bool = skeletonize(cleaned_mask > 0)
        return (skel_bool.astype(np.uint8)) * 255

    def build_road_graph(self, skeleton_image: np.ndarray) -> Tuple[nx.Graph, List[Set]]:
        """Build 8-connected NetworkX Graph from 1-pixel skeleton image."""
        skel_bool = skeleton_image > 0
        ys, xs = np.where(skel_bool)
        skel_set = set(zip(xs, ys))

        G = nx.Graph()

        for x, y in skel_set:
            G.add_node((int(x), int(y)))
            for dx, dy in NEIGHBORS:
                nx_pos, ny_pos = x + dx, y + dy
                if (nx_pos, ny_pos) in skel_set:
                    dist = float(np.sqrt(dx * dx + dy * dy))
                    G.add_edge((int(x), int(y)), (int(nx_pos), int(ny_pos)), weight=dist)

        connected_components = list(nx.connected_components(G))
        return G, connected_components

    def export_geojson(
        self,
        G: nx.Graph,
        connected_components: List[Set],
        output_filepath: Path,
    ) -> Dict[str, Any]:
        """Convert NetworkX road graph to pixel-coordinate GeoJSON FeatureCollection."""
        largest_comp = max(connected_components, key=len) if connected_components else set()

        # Identify key nodes: junctions (degree >= 3) and endpoints (degree == 1)
        degree_map = dict(G.degree())
        junctions = {n for n, deg in degree_map.items() if deg >= 3}
        endpoints = {n for n, deg in degree_map.items() if deg == 1}
        key_nodes = junctions.union(endpoints)

        features = []
        visited_edges = set()
        road_counter = 0

        # Trace corridors between key nodes
        for start_node in key_nodes:
            for nbr in G.neighbors(start_node):
                edge_key = tuple(sorted([start_node, nbr]))
                if edge_key in visited_edges:
                    continue
                visited_edges.add(edge_key)

                # Trace path along degree 2 nodes until reaching another key node
                path_pixels = [start_node, nbr]
                curr = nbr
                prev = start_node

                while curr not in key_nodes:
                    nbrs = list(G.neighbors(curr))
                    next_node = None
                    for n in nbrs:
                        if n != prev:
                            next_node = n
                            break
                    if next_node is None:
                        break
                    path_pixels.append(next_node)
                    prev = curr
                    curr = next_node

                # Calculate length in pixels
                length_px = 0.0
                for i in range(len(path_pixels) - 1):
                    p1, p2 = path_pixels[i], path_pixels[i + 1]
                    length_px += np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

                is_in_largest = (start_node in largest_comp)

                feature = {
                    "type": "Feature",
                    "properties": {
                        "road_id": f"road-{road_counter}",
                        "length_pixels": round(float(length_px), 2),
                        "connected": is_in_largest,
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[int(pt[0]), int(pt[1])] for pt in path_pixels],
                    },
                }
                features.append(feature)
                road_counter += 1

        # Fallback if no junction/endpoints traced (e.g. simple edges)
        if not features and G.number_of_edges() > 0:
            for idx, (u, v, data) in enumerate(G.edges(data=True)):
                length_px = data.get("weight", 1.0)
                feature = {
                    "type": "Feature",
                    "properties": {
                        "road_id": f"road-{idx}",
                        "length_pixels": round(float(length_px), 2),
                        "connected": (u in largest_comp),
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[int(u[0]), int(u[1])], [int(v[0]), int(v[1])]],
                    },
                }
                features.append(feature)

        geojson_data = {
            "type": "FeatureCollection",
            "features": features,
        }

        output_filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(output_filepath, "w") as f:
            json.dump(geojson_data, f, indent=2)

        return geojson_data

    def generate_visualizations(
        self,
        sat_path: Optional[Path],
        mask: np.ndarray,
        skeleton: np.ndarray,
        G: nx.Graph,
        output_dir: Path,
    ) -> Dict[str, Path]:
        """Generate output images: road_skeleton.png, road_network_overlay.png, prediction_comparison.png."""
        output_dir.mkdir(parents=True, exist_ok=True)
        height, width = mask.shape[:2]

        # 1. Save road_skeleton.png
        skel_path = output_dir / "road_skeleton.png"
        cv2.imwrite(str(skel_path), skeleton)

        # Load satellite base image or create black canvas if sat_path missing
        if sat_path and Path(sat_path).exists():
            sat_bgr = cv2.imread(str(sat_path), cv2.IMREAD_COLOR)
            sat_bgr = cv2.resize(sat_bgr, (width, height))
            sat_rgb = cv2.cvtColor(sat_bgr, cv2.COLOR_BGR2RGB)
        else:
            sat_rgb = np.zeros((height, width, 3), dtype=np.uint8)

        # 2. Save road_network_overlay.png
        overlay_pil = Image.fromarray(sat_rgb.copy())
        draw = ImageDraw.Draw(overlay_pil)

        # Draw extracted skeleton lines in bright cyan
        for u, v in G.edges():
            draw.line([u, v], fill=(0, 255, 255), width=2)

        # Draw junction nodes (degree >= 3 in ORANGE, endpoints degree == 1 in CYAN)
        for node, deg in G.degree():
            nx_p, ny_p = node
            if deg >= 3:
                draw.ellipse([nx_p - 3, ny_p - 3, nx_p + 3, ny_p + 3], fill=(255, 140, 0), outline=(255, 255, 255))
            elif deg == 1:
                draw.ellipse([nx_p - 2, ny_p - 2, nx_p + 2, ny_p + 2], fill=(0, 255, 255), outline=(0, 0, 0))

        overlay_path = output_dir / "road_network_overlay.png"
        overlay_pil.save(overlay_path)

        # 3. Save prediction_comparison.png (4-Panel Quadrant Grid)
        # Panel 1: Original Satellite Image (RGB)
        panel1 = sat_rgb.copy()

        # Panel 2: U-Net Binary Prediction Mask (RGB)
        mask_rgb = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB) if len(mask.shape) == 2 else mask
        panel2 = cv2.resize(mask_rgb, (width, height))

        # Panel 3: Extracted Road Skeleton (RGB)
        skel_rgb = cv2.cvtColor(skeleton, cv2.COLOR_GRAY2RGB) if len(skeleton.shape) == 2 else skeleton
        panel3 = cv2.resize(skel_rgb, (width, height))

        # Panel 4: Road Network Overlay (RGB)
        panel4 = np.array(overlay_pil)

        # Helper to draw title label banner on top of each panel
        def add_panel_label(img_np: np.ndarray, text: str) -> np.ndarray:
            pil_img = Image.fromarray(img_np)
            d = ImageDraw.Draw(pil_img)
            d.rectangle([5, 5, 240, 30], fill=(15, 23, 42, 220), outline=(51, 65, 85))
            d.text((12, 10), text, fill=(241, 245, 249))
            return np.array(pil_img)

        p1_labeled = add_panel_label(panel1, "1. ORIGINAL SATELLITE")
        p2_labeled = add_panel_label(panel2, "2. AI PREDICTION MASK")
        p3_labeled = add_panel_label(panel3, "3. ROAD SKELETON")
        p4_labeled = add_panel_label(panel4, "4. ROAD NETWORK OVERLAY")

        top_row = np.hstack([p1_labeled, p2_labeled])
        bottom_row = np.hstack([p3_labeled, p4_labeled])
        comparison_grid = np.vstack([top_row, bottom_row])

        comparison_path = output_dir / "prediction_comparison.png"
        Image.fromarray(comparison_grid).save(comparison_path)

        return {
            "road_skeleton.png": skel_path,
            "road_network_overlay.png": overlay_path,
            "prediction_comparison.png": comparison_path,
        }

    def process_road_network(
        self,
        mask_path: Union[str, Path],
        sat_path: Optional[Union[str, Path]] = None,
        output_dir: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """Execute full road network extraction pipeline on prediction mask."""
        m_file = Path(mask_path)
        if not m_file.exists():
            raise FileNotFoundError(f"Prediction mask file not found at '{m_file}'")

        raw_mask = cv2.imread(str(m_file), cv2.IMREAD_GRAYSCALE)
        if raw_mask is None:
            raise ValueError(f"Failed to read image mask at '{m_file}'")

        out_dir = Path(output_dir) if output_dir else m_file.parent

        # 1. Clean mask
        cleaned_mask = self.clean_road_mask(raw_mask)

        # 2. Extract skeleton
        skel = self.extract_skeleton(cleaned_mask)

        # 3. Build Graph
        G, connected_comps = self.build_road_graph(skel)

        # 4. Compute statistics
        total_pixels = raw_mask.size
        road_pixels = int(np.sum(cleaned_mask > 0))
        road_pct = (road_pixels / total_pixels) * 100.0

        graph_nodes = G.number_of_nodes()
        graph_edges = G.number_of_edges()
        num_components = len(connected_comps)
        largest_comp_nodes = len(max(connected_comps, key=len)) if connected_comps else 0

        # 5. Export GeoJSON
        geojson_path = out_dir / "road_network.geojson"
        geojson_data = self.export_geojson(G, connected_comps, geojson_path)

        # 6. Generate output visualization images
        s_path = Path(sat_path) if sat_path else None
        vis_paths = self.generate_visualizations(s_path, cleaned_mask, skel, G, out_dir)

        logger.info(
            f"Road network extraction complete: Nodes={graph_nodes}, Edges={graph_edges}, Comps={num_components}"
        )

        return {
            "road_pixels": road_pixels,
            "road_coverage_percentage": round(road_pct, 2),
            "graph_nodes": graph_nodes,
            "graph_edges": graph_edges,
            "connected_components": num_components,
            "largest_component_nodes": largest_comp_nodes,
            "skeleton_path": str(vis_paths["road_skeleton.png"]),
            "overlay_path": str(vis_paths["road_network_overlay.png"]),
            "comparison_path": str(vis_paths["prediction_comparison.png"]),
            "geojson_path": str(geojson_path),
            "geojson": geojson_data,
        }


road_network_service = RoadNetworkService()
