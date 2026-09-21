import math
import time
import uuid
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import networkx as nx

# Ensure backend directory is in sys.path
AI_DIR = Path(__file__).resolve().parent.parent.parent / "ai"
BACKEND_DIR = AI_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ai.georeference import GeoReferenceTransform, georeference, haversine_distance_km, DEFAULT_BOUNDS
from app.services.ai_service import get_road_predictor
from app.utils.logging import get_logger

logger = get_logger("app.services.emergency_routing_service")

# Emergency Vehicle Speeds (km/h)
VEHICLE_SPEEDS_KMH = {
    "ambulance": 50.0,
    "fire_truck": 40.0,
    "rescue": 45.0,
    "police": 55.0,
    "default": 40.0,
}

# Confidence Weighting Penalty Multiplier
BETA_CONFIDENCE = 1.5

# Max snapping distance in meters
MAX_SNAP_DISTANCE_METERS = 100.0


def _bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate compass bearing in degrees between two geographic points."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)

    theta = math.atan2(y, x)
    bearing = (math.degrees(theta) + 360.0) % 360.0
    return bearing


def _get_turn_type(bearing_diff: float) -> str:
    """Classify heading change angle (-180 to 180) into turn type maneuver."""
    if -20.0 <= bearing_diff <= 20.0:
        return "straight"
    elif 20.0 < bearing_diff <= 60.0:
        return "slight_right"
    elif 60.0 < bearing_diff <= 135.0:
        return "right"
    elif -60.0 <= bearing_diff < -20.0:
        return "slight_left"
    elif -135.0 <= bearing_diff < -60.0:
        return "left"
    else:
        return "u_turn"


class EmergencyRoutingService:
    """Production AI Emergency Routing Engine for RESQROUTE.

    Performs point-to-road-segment snapping, edge splitting, confidence-weighted Dijkstra routing,
    geographic WGS84 coordinate conversion, and turn-by-turn maneuver generation.
    """

    def __init__(self, geo_transform: Optional[GeoReferenceTransform] = None):
        self.geo = geo_transform or georeference
        self._cached_graph: Optional[nx.Graph] = None
        self._cached_prob_map: Optional[np.ndarray] = None

    def get_active_ai_graph(self) -> Tuple[nx.Graph, Optional[np.ndarray]]:
        """Retrieve or initialize the active AI road graph for the georeferenced area."""
        if self._cached_graph is None:
            logger.info("Building baseline AI road network graph for georeferenced area...")
            predictor = get_road_predictor()
            sample_img = AI_DIR / "datasets" / "processed" / "images" / "chip0.png"
            if not sample_img.exists():
                raise FileNotFoundError(f"Sample satellite image missing at '{sample_img}'")
            
            res = predictor.predict(sample_img, threshold=0.25, extract_network=True)
            self._cached_graph = res["road_network"]["graph"]
            self._cached_prob_map = res["probability_map"]

        return self._cached_graph, self._cached_prob_map

    def snap_point_to_graph_edge(
        self,
        graph: nx.Graph,
        target_lat: float,
        target_lng: float,
        max_distance_meters: float = MAX_SNAP_DISTANCE_METERS,
    ) -> Dict[str, Any]:
        """Find the closest point on any AI graph edge polyline to target (lat, lng).

        Returns:
            Dict containing snapped pixel, snapped geo coord, distance in meters, matched edge, segment index.
        """
        tx_px, ty_px = self.geo.geo_to_pixel(target_lat, target_lng)
        min_dist_m = float("inf")
        best_snap_px = None
        best_snap_geo = None
        best_edge = None
        best_segment_idx = 0

        for u, v, data in graph.edges(data=True):
            pts = data.get("points") or data.get("geometry") or [graph.nodes[u]["pos"], graph.nodes[v]["pos"]]
            
            for i in range(len(pts) - 1):
                p1_x, p1_y = pts[i]
                p2_x, p2_y = pts[i + 1]

                # Project target pixel onto segment P1-P2
                dx = p2_x - p1_x
                dy = p2_y - p1_y
                seg_len_sq = dx * dx + dy * dy

                if seg_len_sq == 0:
                    c_x, c_y = p1_x, p1_y
                else:
                    t = max(0.0, min(1.0, ((tx_px - p1_x) * dx + (ty_px - p1_y) * dy) / seg_len_sq))
                    c_x = p1_x + t * dx
                    c_y = p1_y + t * dy

                c_lat, c_lng = self.geo.pixel_to_geo(c_x, c_y)
                dist_m = haversine_distance_km(target_lat, target_lng, c_lat, c_lng) * 1000.0

                if dist_m < min_dist_m:
                    min_dist_m = dist_m
                    best_snap_px = (float(c_x), float(c_y))
                    best_snap_geo = (float(c_lat), float(c_lng))
                    best_edge = (u, v)
                    best_segment_idx = i

        is_valid = min_dist_m <= max_distance_meters
        return {
            "valid": is_valid,
            "edge": best_edge,
            "segment_idx": best_segment_idx,
            "snap_pixel": best_snap_px,
            "snap_geo": best_snap_geo,
            "distance_meters": round(min_dist_m, 2),
        }

    def _inject_snapped_node(
        self,
        G: nx.Graph,
        snap_info: Dict[str, Any],
        temp_node_id: Any,
    ) -> None:
        """Inject snapped location into graph by splitting the matched edge."""
        u, v = snap_info["edge"]
        snap_px = snap_info["snap_pixel"]
        snap_geo = snap_info["snap_geo"]
        seg_idx = snap_info["segment_idx"]

        edge_data = G.get_edge_data(u, v)
        if not edge_data:
            # Fallback to connected sub-edge if (u, v) was already split by a prior snapped node
            for n1, n2 in list(G.edges()):
                if n1 in (u, v) or n2 in (u, v):
                    e_candidate = G.get_edge_data(n1, n2)
                    if e_candidate:
                        u, v = n1, n2
                        edge_data = e_candidate
                        break
        if not edge_data:
            # Emergency fallback: add node directly to graph if edge data unavailable
            G.add_node(
                temp_node_id,
                x=snap_px[0],
                y=snap_px[1],
                pos=snap_px,
                lat=snap_geo[0],
                lng=snap_geo[1],
            )
            # Connect to nearest node
            nearest_n = u if u in G else (v if v in G else list(G.nodes())[0])
            G.add_edge(temp_node_id, nearest_n, weight=0.1, length=1.0, confidence=1.0, points=[snap_px, G.nodes[nearest_n]["pos"]])
            return

        pts = list(edge_data.get("points") or edge_data.get("geometry") or [G.nodes[u]["pos"], G.nodes[v]["pos"]])
        conf = edge_data.get("confidence", 1.0)

        # Split points polyline into two parts
        pts_part1 = pts[: seg_idx + 1] + [snap_px]
        pts_part2 = [snap_px] + pts[seg_idx + 1 :]

        # Add temporary snapped node
        G.add_node(
            temp_node_id,
            x=snap_px[0],
            y=snap_px[1],
            pos=snap_px,
            lat=snap_geo[0],
            lng=snap_geo[1],
        )

        # Remove original edge and insert split sub-edges
        G.remove_edge(u, v)

        # Helper to compute sub-edge properties
        for node_a, node_b, sub_pts in [(u, temp_node_id, pts_part1), (temp_node_id, v, pts_part2)]:
            length_m = 0.0
            for k in range(len(sub_pts) - 1):
                p1_lat, p1_lng = self.geo.pixel_to_geo(sub_pts[k][0], sub_pts[k][1])
                p2_lat, p2_lng = self.geo.pixel_to_geo(sub_pts[k + 1][0], sub_pts[k + 1][1])
                length_m += haversine_distance_km(p1_lat, p1_lng, p2_lat, p2_lng) * 1000.0

            weight_cost = length_m * (1.0 + BETA_CONFIDENCE * (1.0 - conf))
            G.add_edge(
                node_a,
                node_b,
                weight=weight_cost,
                length=length_m,
                confidence=conf,
                points=sub_pts,
            )

    def calculate_emergency_route(
        self,
        start_lat: float,
        start_lng: float,
        dest_lat: float,
        dest_lng: float,
        start_name: Optional[str] = None,
        dest_name: Optional[str] = None,
        vehicle_type: str = "ambulance",
        avoid_low_confidence: bool = True,
    ) -> Dict[str, Any]:
        """Calculate real road-following emergency route on AI extracted road network graph.

        Returns structured result dict.
        """
        # 1. Bounds Validation
        if not self.geo.is_within_bounds(start_lat, start_lng):
            return {
                "success": False,
                "status": "out_of_bounds",
                "message": f"Start location [{start_lat}, {start_lng}] is outside the active georeferenced satellite area.",
            }

        if not self.geo.is_within_bounds(dest_lat, dest_lng):
            return {
                "success": False,
                "status": "out_of_bounds",
                "message": f"Destination location [{dest_lat}, {dest_lng}] is outside the active georeferenced satellite area.",
            }

        # 2. Get baseline AI road graph
        base_graph, prob_map = self.get_active_ai_graph()
        if base_graph.number_of_nodes() == 0:
            return {
                "success": False,
                "status": "no_path_found",
                "message": "AI road network graph is empty. No roads detected.",
            }

        # 3. Snap start and destination to AI graph edges
        start_snap = self.snap_point_to_graph_edge(base_graph, start_lat, start_lng)
        if not start_snap["valid"]:
            return {
                "success": False,
                "status": "off_road",
                "message": f"Start location is too far ({start_snap['distance_meters']}m) from the detected AI road network (max {MAX_SNAP_DISTANCE_METERS}m).",
            }

        dest_snap = self.snap_point_to_graph_edge(base_graph, dest_lat, dest_lng)
        if not dest_snap["valid"]:
            return {
                "success": False,
                "status": "off_road",
                "message": f"Destination location is too far ({dest_snap['distance_meters']}m) from the detected AI road network (max {MAX_SNAP_DISTANCE_METERS}m).",
            }

        # 4. Create working copy of graph and inject snapped nodes
        G_work = base_graph.copy()
        start_node_id = "TEMP_START_NODE"
        dest_node_id = "TEMP_DEST_NODE"

        self._inject_snapped_node(G_work, start_snap, start_node_id)
        self._inject_snapped_node(G_work, dest_snap, dest_node_id)

        # 5. Connected Component Check
        if not nx.has_path(G_work, start_node_id, dest_node_id):
            return {
                "success": False,
                "status": "no_path_found",
                "message": "No connected AI road route exists between the selected locations.",
            }

        # 6. Run Dijkstra's Algorithm for shortest weighted path
        try:
            node_path = nx.dijkstra_path(G_work, start_node_id, dest_node_id, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
            return {
                "success": False,
                "status": "no_path_found",
                "message": f"Dijkstra path calculation failed: {str(e)}",
            }

        # 7. Reconstruct route polyline points (in pixel & geographic coords)
        full_pixel_points: List[Tuple[float, float]] = []
        edge_confidences: List[float] = []

        for k in range(len(node_path) - 1):
            u_n, v_n = node_path[k], node_path[k + 1]
            e_data = G_work.get_edge_data(u_n, v_n)
            e_pts = e_data.get("points") or e_data.get("geometry") or []
            conf = e_data.get("confidence", 1.0)
            edge_confidences.append(conf)

            if not full_pixel_points:
                full_pixel_points.extend(e_pts)
            else:
                # Append points excluding redundant overlap
                if e_pts and full_pixel_points[-1] == e_pts[0]:
                    full_pixel_points.extend(e_pts[1:])
                elif e_pts and full_pixel_points[-1] == e_pts[-1]:
                    full_pixel_points.extend(reversed(e_pts[:-1]))
                else:
                    full_pixel_points.extend(e_pts)

        # Convert pixels to WGS84 GeoJSON [lng, lat] format
        geojson_coords: List[List[float]] = []
        for px, py in full_pixel_points:
            c_lat, c_lng = self.geo.pixel_to_geo(px, py)
            coord_item = [round(c_lng, 6), round(c_lat, 6)]
            if not geojson_coords or geojson_coords[-1] != coord_item:
                geojson_coords.append(coord_item)

        # Calculate exact total route distance in meters via Haversine
        total_dist_meters = 0.0
        for i in range(len(geojson_coords) - 1):
            p1_lng, p1_lat = geojson_coords[i]
            p2_lng, p2_lat = geojson_coords[i + 1]
            total_dist_meters += haversine_distance_km(p1_lat, p1_lng, p2_lat, p2_lng) * 1000.0

        total_dist_meters = round(total_dist_meters, 1)

        # Calculate travel duration
        speed_kmh = VEHICLE_SPEEDS_KMH.get(vehicle_type.lower(), VEHICLE_SPEEDS_KMH["default"])
        speed_mps = (speed_kmh * 1000.0) / 3600.0
        duration_seconds = int(round(total_dist_meters / speed_mps)) if speed_mps > 0 else 0

        # Calculate average confidence and risk level
        avg_confidence = float(np.mean(edge_confidences)) if edge_confidences else 1.0
        avg_confidence = round(max(0.0, min(1.0, avg_confidence)), 3)

        if avg_confidence >= 0.75:
            risk_level = "low"
        elif avg_confidence >= 0.50:
            risk_level = "moderate"
        else:
            risk_level = "high"

        # 8. Generate Turn-by-Turn Maneuvers (`steps`)
        steps = []
        if len(geojson_coords) >= 2:
            # Step 1: Start
            start_coord = geojson_coords[0]
            steps.append({
                "id": "step_1",
                "instruction": f"Start emergency response on AI detected road network near {start_name or 'origin'}",
                "distance_meters": 0.0,
                "duration_seconds": 0,
                "road_name": "AI Extracted Road Segment 1",
                "turn_type": "start",
                "location": start_coord,
            })

            # Intermediate maneuvers based on bearing changes
            step_counter = 2
            accumulated_dist = 0.0
            accumulated_dur = 0
            prev_bearing = _bearing_degrees(geojson_coords[0][1], geojson_coords[0][0], geojson_coords[1][1], geojson_coords[1][0])

            for i in range(1, len(geojson_coords) - 1):
                p_prev_lng, p_prev_lat = geojson_coords[i - 1]
                p_curr_lng, p_curr_lat = geojson_coords[i]
                p_next_lng, p_next_lat = geojson_coords[i + 1]

                seg_dist = haversine_distance_km(p_prev_lat, p_prev_lng, p_curr_lat, p_curr_lng) * 1000.0
                seg_dur = int(round(seg_dist / speed_mps)) if speed_mps > 0 else 0
                accumulated_dist += seg_dist
                accumulated_dur += seg_dur

                curr_bearing = _bearing_degrees(p_curr_lat, p_curr_lng, p_next_lat, p_next_lng)
                bearing_diff = (curr_bearing - prev_bearing + 540.0) % 360.0 - 180.0

                turn_type = _get_turn_type(bearing_diff)
                if turn_type != "straight":
                    turn_label = turn_type.replace("_", " ")
                    steps.append({
                        "id": f"step_{step_counter}",
                        "instruction": f"Turn {turn_label} onto AI Extracted Road Segment {step_counter}",
                        "distance_meters": round(accumulated_dist, 1),
                        "duration_seconds": accumulated_dur,
                        "road_name": f"AI Extracted Road Segment {step_counter}",
                        "turn_type": turn_type,
                        "location": p_curr,
                    } if (p_curr := [p_curr_lng, p_curr_lat]) else {})
                    step_counter += 1
                    accumulated_dist = 0.0
                    accumulated_dur = 0
                    prev_bearing = curr_bearing

            # Final Step: Arrive
            end_coord = geojson_coords[-1]
            last_dist = haversine_distance_km(geojson_coords[-2][1], geojson_coords[-2][0], end_coord[1], end_coord[0]) * 1000.0
            last_dur = int(round(last_dist / speed_mps)) if speed_mps > 0 else 0
            accumulated_dist += last_dist
            accumulated_dur += last_dur

            steps.append({
                "id": f"step_{step_counter}",
                "instruction": f"Arrive at emergency destination ({dest_name or 'target zone'})",
                "distance_meters": round(accumulated_dist, 1),
                "duration_seconds": accumulated_dur,
                "road_name": "Destination",
                "turn_type": "arrive",
                "location": end_coord,
            })

        route_id = f"route_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"

        return {
            "success": True,
            "route_id": route_id,
            "status": "calculated",
            "routing_engine": "resqroute_ai_graph",
            "total_distance_meters": total_dist_meters,
            "estimated_duration_seconds": duration_seconds,
            "average_confidence": avg_confidence,
            "risk_level": risk_level,
            "snapped_start": {
                "lat": start_snap["snap_geo"][0],
                "lng": start_snap["snap_geo"][1],
                "distance_to_road_meters": start_snap["distance_meters"],
            },
            "snapped_destination": {
                "lat": dest_snap["snap_geo"][0],
                "lng": dest_snap["snap_geo"][1],
                "distance_to_road_meters": dest_snap["distance_meters"],
            },
            "geometry": {
                "type": "LineString",
                "coordinates": geojson_coords,
            },
            "steps": steps,
        }


# Singleton service instance
emergency_routing_service = EmergencyRoutingService()


def calculate_emergency_route(*args, **kwargs) -> Dict[str, Any]:
    """Module-level convenience wrapper for emergency_routing_service.calculate_emergency_route."""
    return emergency_routing_service.calculate_emergency_route(*args, **kwargs)

