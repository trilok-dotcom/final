import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.db.database import get_db_connection
from app.schemas.rescue_unit import RescueUnitCreate, RescueUnitUpdate
from app.utils.logging import get_logger

logger = get_logger("app.services.rescue_unit_service")


class RescueUnitService:
    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        """Convert SQLite Row to dictionary with parsed json capabilities."""
        d = dict(row)
        if "capabilities" in d and isinstance(d["capabilities"], str):
            try:
                d["capabilities"] = json.loads(d["capabilities"])
            except Exception:
                d["capabilities"] = []
        return d

    @classmethod
    def list_rescue_units(
        cls,
        status: Optional[str] = None,
        unit_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            query = "SELECT * FROM rescue_units WHERE 1=1"
            params = []
            if status:
                query += " AND UPPER(status) = ?"
                params.append(status.upper())
            if unit_type:
                query += " AND UPPER(unit_type) = ?"
                params.append(unit_type.upper())

            query += " ORDER BY unit_code ASC;"
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [cls._row_to_dict(r) for r in rows]
        finally:
            conn.close()

    @classmethod
    def get_rescue_unit(cls, unit_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM rescue_units WHERE id = ? OR UPPER(unit_code) = ?;", (unit_id, unit_id.upper()))
            row = cursor.fetchone()
            if not row:
                return None
            return cls._row_to_dict(row)
        finally:
            conn.close()

    @classmethod
    def create_rescue_unit(cls, data: RescueUnitCreate) -> Dict[str, Any]:
        # Check duplicate unit_code
        existing = cls.get_rescue_unit(data.unit_code)
        if existing:
            raise ValueError(f"Rescue unit with code '{data.unit_code}' already exists.")

        unit_id = f"unit-{uuid.uuid4().hex[:8]}"
        now_iso = datetime.utcnow().isoformat() + "Z"
        caps_json = json.dumps(data.capabilities or [])

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO rescue_units (
                    id, unit_code, unit_type, status, latitude, longitude,
                    name, crew_size, capabilities, current_incident_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    unit_id,
                    data.unit_code.upper(),
                    data.unit_type,
                    data.status or "AVAILABLE",
                    data.latitude,
                    data.longitude,
                    data.name,
                    data.crew_size,
                    caps_json,
                    data.current_incident_id,
                    now_iso,
                    now_iso,
                ),
            )
            conn.commit()
            logger.info(f"Created rescue unit {data.unit_code} ({unit_id})")
            return cls.get_rescue_unit(unit_id)
        finally:
            conn.close()

    @classmethod
    def update_rescue_unit(cls, unit_id: str, data: RescueUnitUpdate) -> Optional[Dict[str, Any]]:
        existing = cls.get_rescue_unit(unit_id)
        if not existing:
            return None

        if isinstance(data, dict):
            update_dict = data.copy()
        elif hasattr(data, "model_dump"):
            update_dict = data.model_dump(exclude_unset=True)
        else:
            update_dict = dict(data)
        if not update_dict:
            return existing

        if "capabilities" in update_dict and isinstance(update_dict["capabilities"], list):
            update_dict["capabilities"] = json.dumps(update_dict["capabilities"])

        update_dict["updated_at"] = datetime.utcnow().isoformat() + "Z"

        fields = []
        params = []
        for k, v in update_dict.items():
            fields.append(f"{k} = ?")
            params.append(v)

        params.append(existing["id"])

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE rescue_units SET {', '.join(fields)} WHERE id = ?;", params)
            conn.commit()
            return cls.get_rescue_unit(existing["id"])
        finally:
            conn.close()

    @classmethod
    def update_status(cls, unit_id: str, status: str) -> Optional[Dict[str, Any]]:
        existing = cls.get_rescue_unit(unit_id)
        if not existing:
            return None

        now_iso = datetime.utcnow().isoformat() + "Z"
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE rescue_units SET status = ?, updated_at = ? WHERE id = ?;",
                (status.upper(), now_iso, existing["id"]),
            )
            conn.commit()
            return cls.get_rescue_unit(existing["id"])
        finally:
            conn.close()

    @classmethod
    def delete_rescue_unit(cls, unit_id: str) -> bool:
        existing = cls.get_rescue_unit(unit_id)
        if not existing:
            return False
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM rescue_units WHERE id = ?;", (existing["id"],))
            conn.commit()
            return True
        finally:
            conn.close()


rescue_unit_service = RescueUnitService()
