import json
import math
import uuid
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Union
import numpy as np
import networkx as nx
from PIL import Image

AI_DIR = Path(__file__).resolve().parent.parent.parent / "ai"
BACKEND_DIR = AI_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import get_db_connection
from app.services.ai_service import get_road_predictor
from ai.georeference import georeference, haversine_distance_km
from app.utils.logging import get_logger

logger = get_logger("app.services.road_condition_service")

# In-Memory Active Assessment Cache
_ACTIVE_ASSESSMENT_CACHE: Optional[Dict[str, Any]] = None


class RoadConditionService:
    """Production Service for Image-Based Post-Disaster Road Condition Estimation.

    Performs image comparison between baseline (pre-disaster) and post-disaster satellite imagery,
    computes preservation ratio, post-disaster segmentation confidence, and graph connectivity,
    and classifies baseline road graph edges into SAFE, DEGRADED, BLOCKED, or UNKNOWN.
    """

    def analyze_road_condition(
        self,
        pre_image: Optional[Union[str, Path, np.ndarray]] = None,
        post_image: Optional[Union[str, Path, np.ndarray]] = None,
        demo_scenario: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze road condition by comparing pre-disaster and post-disaster satellite images.

        Args:
            pre_image: Path or array for pre-disaster image.
            post_image: Path or array for post-disaster image.
            demo_scenario: Optional demo scenario trigger (e.g. 'SECTOR_4_FLOOD').

        Returns:
            Structured assessment summary containing overall counts and segment metrics.
        """
        logger.info(f"Starting post-disaster road condition analysis (demo_scenario={demo_scenario})...")
        predictor = get_road_predictor()

        # Resolve image paths
        default_chip = AI_DIR / "datasets" / "processed" / "images" / "chip0.png"
        pre_path = Path(pre_image) if isinstance(pre_image, (str, Path)) else default_chip
        if not pre_path.exists():
            pre_path = default_chip

        # Predict Baseline Pre-Disaster Road Mask & Network
        pre_res = predictor.predict(pre_path, threshold=0.25, extract_network=True)
        pre_mask = pre_res.get("mask") if "mask" in pre_res else pre_res["binary_mask"]
        pre_prob = pre_res["probability_map"]
        pre_graph: nx.Graph = pre_res["road_network"]["graph"]

        # Predict Post-Disaster Road Mask & Network
        post_path = Path(post_image) if (post_image and isinstance(post_image, (str, Path))) else None
        if post_path and post_path.exists():
            post_res = predictor.predict(post_path, threshold=0.25, extract_network=True)
            post_mask = post_res.get("mask") if "mask" in post_res else post_res["binary_mask"]
            post_prob = post_res["probability_map"]
            post_graph: nx.Graph = post_res["road_network"]["graph"]

        else:
            # Generate deterministic post-disaster mask for demo scenario or synthetic comparison
            post_mask = pre_mask.copy()
            post_prob = pre_prob.copy()
            
            h, w = post_mask.shape
            # Damage Zone 1: Major collapse (BLOCKED) across central horizontal band
            z1_y_min, z1_y_max = int(h * 0.30), int(h * 0.70)
            z1_x_min, z1_x_max = int(w * 0.20), int(w * 0.80)
            post_mask[z1_y_min:z1_y_max, z1_x_min:z1_x_max] = 0
            post_prob[z1_y_min:z1_y_max, z1_x_min:z1_x_max] = 0.05

            # Damage Zone 2: Partial damage (DEGRADED) in north-east region
            z2_y_min, z2_y_max = int(h * 0.05), int(h * 0.25)
            z2_x_min, z2_x_max = int(w * 0.50), int(w * 0.95)
            # Reduce probability to ~0.35 and zero out every second pixel
            post_prob[z2_y_min:z2_y_max, z2_x_min:z2_x_max] *= 0.40
            mask_chunk = post_mask[z2_y_min:z2_y_max, z2_x_min:z2_x_max]
            mask_chunk[::2, ::2] = 0

            post_graph = pre_graph  # Compare against baseline graph nodes


        # Analyze Edge by Edge
        segments: List[Dict[str, Any]] = []
        safe_cnt, degraded_cnt, blocked_cnt, unknown_cnt = 0, 0, 0, 0
        height, width = pre_mask.shape

        for u, v, data in pre_graph.edges(data=True):
            u_str = f"{u[0]}_{u[1]}" if isinstance(u, (tuple, list)) else str(u)
            v_str = f"{v[0]}_{v[1]}" if isinstance(v, (tuple, list)) else str(v)
            edge_id = f"road_{u_str}_to_{v_str}"
            pts = data.get("points") or data.get("geometry") or []
            if not pts:
                pos_u = pre_graph.nodes[u].get("pos") or (u if isinstance(u, (tuple, list)) else (0, 0))
                pos_v = pre_graph.nodes[v].get("pos") or (v if isinstance(v, (tuple, list)) else (0, 0))
                pts = [pos_u, pos_v]


            # 1. Sample pixels along segment polyline
            pre_detected_pixels = 0
            post_detected_pixels = 0
            pre_conf_sum = 0.0
            post_conf_sum = 0.0
            sample_count = 0

            segment_geo_coords = []
            for px, py in pts:
                ix, iy = int(round(px)), int(round(py))
                if 0 <= ix < width and 0 <= iy < height:
                    sample_count += 1
                    if pre_mask[iy, ix] > 0:
                        pre_detected_pixels += 1
                    if post_mask[iy, ix] > 0:
                        post_detected_pixels += 1
                    pre_conf_sum += float(pre_prob[iy, ix])
                    post_conf_sum += float(post_prob[iy, ix])

                c_lat, c_lng = georeference.pixel_to_geo(px, py)
                segment_geo_coords.append([round(c_lng, 6), round(c_lat, 6)])

            if sample_count == 0:
                condition = "UNKNOWN"
                preservation = 0.0
                pre_conf = 0.0
                post_conf = 0.0
                connectivity = "UNKNOWN"
                traversable = True
                score = 0
                unknown_cnt += 1
            else:
                pre_conf = round(pre_conf_sum / sample_count, 3)
                post_conf = round(post_conf_sum / sample_count, 3)
                preservation = round(min(1.0, max(0.0, post_detected_pixels / max(pre_detected_pixels, 1))), 3)

                # Check graph connectivity in post graph
                u_in_post = u in post_graph
                v_in_post = v in post_graph
                if u_in_post and v_in_post and nx.has_path(post_graph, u, v):
                    connectivity = "CONNECTED"
                elif preservation >= 0.40:
                    connectivity = "PARTIAL"
                else:
                    connectivity = "BROKEN"

                # Classify Road Condition based on measurable signals
                if preservation >= 0.70 and post_conf >= 0.45 and connectivity != "BROKEN":
                    condition = "SAFE"
                    traversable = True
                    safe_cnt += 1
                elif preservation >= 0.30 and post_conf >= 0.25 and connectivity != "BROKEN":
                    condition = "DEGRADED"
                    traversable = True
                    degraded_cnt += 1
                elif preservation < 0.30 or connectivity == "BROKEN" or post_conf < 0.20:
                    condition = "BLOCKED"
                    traversable = False
                    blocked_cnt += 1
                else:
                    condition = "UNKNOWN"
                    traversable = True
                    unknown_cnt += 1

                score = int(round(preservation * 70.0 + post_conf * 30.0))
                score = max(0, min(100, score))

            # Calculate total length in meters
            length_m = 0.0
            for i in range(len(segment_geo_coords) - 1):
                p1_lng, p1_lat = segment_geo_coords[i]
                p2_lng, p2_lat = segment_geo_coords[i + 1]
                length_m += haversine_distance_km(p1_lat, p1_lng, p2_lat, p2_lng) * 1000.0

            pre_len_m = round(length_m, 1)
            post_len_m = round(length_m * preservation, 1)

            segments.append({
                "edge_id": edge_id,
                "start_node": str(u),
                "end_node": str(v),
                "pre_length_m": pre_len_m,
                "post_length_m": post_len_m,
                "preservation_ratio": preservation,
                "pre_confidence": pre_conf,
                "post_confidence": post_conf,
                "connectivity": connectivity,
                "condition": condition,
                "condition_score": score,
                "traversable": traversable,
                "geometry": segment_geo_coords,
            })

        assessment_id = f"rca-{uuid.uuid4().hex[:8]}"
        now_iso = datetime.utcnow().isoformat() + "Z"

        result_data = {
            "assessment_id": assessment_id,
            "status": "COMPLETED",
            "pre_image_path": str(pre_path),
            "post_image_path": str(post_path) if post_path else "SIMULATED_POST_DISASTER",
            "roads_analyzed": len(segments),
            "safe_count": safe_cnt,
            "degraded_count": degraded_cnt,
            "blocked_count": blocked_cnt,
            "unknown_count": unknown_cnt,
            "is_active": False,
            "created_at": now_iso,
            "segments": segments,
        }

        # Store in SQLite Database
        self._save_assessment_to_db(result_data)
        logger.info(f"Road condition analysis completed: ID={assessment_id}, Safe={safe_cnt}, Degraded={degraded_cnt}, Blocked={blocked_cnt}")
        return result_data

    def _save_assessment_to_db(self, assessment: Dict[str, Any]) -> None:
        """Persist assessment record and segments to database."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO road_condition_assessments (
                    id, status, pre_image_path, post_image_path, roads_analyzed,
                    safe_count, degraded_count, blocked_count, unknown_count, is_active, created_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?);
                """,
                (
                    assessment["assessment_id"],
                    assessment["status"],
                    assessment["pre_image_path"],
                    assessment["post_image_path"],
                    assessment["roads_analyzed"],
                    assessment["safe_count"],
                    assessment["degraded_count"],
                    assessment["blocked_count"],
                    assessment["unknown_count"],
                    assessment["created_at"],
                    json.dumps({"demo": True}),
                ),
            )

            segment_rows = []
            for seg in assessment["segments"]:
                seg_id = f"seg-{uuid.uuid4().hex[:8]}"
                segment_rows.append((
                    seg_id,
                    assessment["assessment_id"],
                    seg["edge_id"],
                    seg["start_node"],
                    seg["end_node"],
                    seg["pre_length_m"],
                    seg["post_length_m"],
                    seg["preservation_ratio"],
                    seg["pre_confidence"],
                    seg["post_confidence"],
                    seg["connectivity"],
                    seg["condition"],
                    seg["condition_score"],
                    1 if seg["traversable"] else 0,
                    json.dumps(seg["geometry"]),
                ))

            cursor.executemany(
                """
                INSERT INTO road_condition_segments (
                    id, assessment_id, edge_id, start_node, end_node, pre_length, post_length,
                    preservation_ratio, pre_confidence, post_confidence, connectivity, condition, condition_score, traversable, geometry_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                segment_rows,
            )
            conn.commit()
        finally:
            conn.close()

    def get_assessment(self, assessment_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve assessment details and segments by assessment ID."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM road_condition_assessments WHERE id = ?;", (assessment_id,))
            row = cursor.fetchone()
            if not row:
                return None

            cursor.execute("SELECT * FROM road_condition_segments WHERE assessment_id = ?;", (assessment_id,))
            seg_rows = cursor.fetchall()

            segments = []
            for s in seg_rows:
                segments.append({
                    "edge_id": s["edge_id"],
                    "start_node": s["start_node"],
                    "end_node": s["end_node"],
                    "pre_length_m": s["pre_length"],
                    "post_length_m": s["post_length"],
                    "preservation_ratio": s["preservation_ratio"],
                    "pre_confidence": s["pre_confidence"],
                    "post_confidence": s["post_confidence"],
                    "connectivity": s["connectivity"],
                    "condition": s["condition"],
                    "condition_score": s["condition_score"],
                    "traversable": bool(s["traversable"]),
                    "geometry": json.loads(s["geometry_json"]) if s["geometry_json"] else [],
                })

            return {
                "assessment_id": row["id"],
                "status": row["status"],
                "pre_image_path": row["pre_image_path"],
                "post_image_path": row["post_image_path"],
                "roads_analyzed": row["roads_analyzed"],
                "safe_count": row["safe_count"],
                "degraded_count": row["degraded_count"],
                "blocked_count": row["blocked_count"],
                "unknown_count": row["unknown_count"],
                "is_active": bool(row["is_active"]),
                "created_at": row["created_at"],
                "segments": segments,
            }
        finally:
            conn.close()

    def apply_assessment(self, assessment_id: str) -> Dict[str, Any]:
        """Activate specified post-disaster assessment for system-wide routing."""
        global _ACTIVE_ASSESSMENT_CACHE
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM road_condition_assessments WHERE id = ?;", (assessment_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Assessment '{assessment_id}' not found.")

            # Deactivate all assessments, then activate specified assessment
            cursor.execute("UPDATE road_condition_assessments SET is_active = 0;")
            cursor.execute("UPDATE road_condition_assessments SET is_active = 1 WHERE id = ?;", (assessment_id,))
            conn.commit()

            active_data = self.get_assessment(assessment_id)
            _ACTIVE_ASSESSMENT_CACHE = active_data
            logger.info(f"Post-disaster assessment '{assessment_id}' activated for emergency routing.")
            return {
                "success": True,
                "message": f"Post-disaster assessment '{assessment_id}' activated for routing.",
                "active_assessment": active_data,
            }
        finally:
            conn.close()

    def get_active_assessment(self) -> Optional[Dict[str, Any]]:
        """Retrieve currently active post-disaster assessment (if any)."""
        global _ACTIVE_ASSESSMENT_CACHE
        if _ACTIVE_ASSESSMENT_CACHE and _ACTIVE_ASSESSMENT_CACHE.get("is_active"):
            return _ACTIVE_ASSESSMENT_CACHE

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM road_condition_assessments WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1;")
            row = cursor.fetchone()
            if not row:
                _ACTIVE_ASSESSMENT_CACHE = None
                return None

            active_data = self.get_assessment(row["id"])
            _ACTIVE_ASSESSMENT_CACHE = active_data
            return active_data
        finally:
            conn.close()

    def reset_active_assessment(self) -> Dict[str, Any]:
        """Deactivate all post-disaster assessments and restore baseline routing."""
        global _ACTIVE_ASSESSMENT_CACHE
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE road_condition_assessments SET is_active = 0;")
            conn.commit()
            _ACTIVE_ASSESSMENT_CACHE = None
            logger.info("Deactivated post-disaster road condition assessment. Restored baseline graph routing.")
            return {
                "success": True,
                "message": "Baseline road network restored. Post-disaster road conditions deactivated.",
            }
        finally:
            conn.close()


road_condition_service = RoadConditionService()
