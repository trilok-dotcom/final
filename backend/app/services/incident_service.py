import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.db.database import get_db_connection
from app.models.incident import Incident
from app.schemas.incident import IncidentCreate, IncidentUpdate
from app.utils.logging import get_logger

logger = get_logger("app.services.incident_service")


class IncidentService:
    @staticmethod
    def generate_incident_code() -> str:
        """Generate human-readable unique incident code like INC-2026-0004."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM incidents;")
            count = cursor.fetchone()[0]
            year = datetime.utcnow().year
            code = f"INC-{year}-{(count + 1):04d}"
            # Check for collisions
            cursor.execute("SELECT id FROM incidents WHERE incident_code = ?;", (code,))
            if cursor.fetchone():
                code = f"INC-{year}-{uuid.uuid4().hex[:4].upper()}"
            return code
        finally:
            conn.close()

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        """Convert SQLite Row to dictionary."""
        d = dict(row)
        return d

    @classmethod
    def list_incidents(
        cls,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        incident_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            query = "SELECT * FROM incidents WHERE 1=1"
            params = []
            if status:
                query += " AND UPPER(status) = ?"
                params.append(status.upper())
            if severity:
                query += " AND UPPER(severity) = ?"
                params.append(severity.upper())
            if incident_type:
                query += " AND UPPER(incident_type) = ?"
                params.append(incident_type.upper())

            query += " ORDER BY created_at DESC;"
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [cls._row_to_dict(r) for r in rows]
        finally:
            conn.close()

    @classmethod
    def get_incident(cls, incident_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM incidents WHERE id = ? OR incident_code = ?;", (incident_id, incident_id))
            row = cursor.fetchone()
            if not row:
                return None
            return cls._row_to_dict(row)
        finally:
            conn.close()

    @classmethod
    def create_incident(cls, data: IncidentCreate) -> Dict[str, Any]:
        inc_id = f"inc-{uuid.uuid4().hex[:8]}"
        code = cls.generate_incident_code()
        now_iso = datetime.utcnow().isoformat() + "Z"

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO incidents (
                    id, incident_code, incident_type, severity, status,
                    latitude, longitude, location_name, description, reported_by,
                    assigned_unit_id, created_at, updated_at, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    inc_id,
                    code,
                    data.incident_type,
                    data.severity,
                    "REPORTED",
                    data.latitude,
                    data.longitude,
                    data.location_name or "Emergency Coordinates Location",
                    data.description or "Emergency incident reported to dispatch.",
                    data.reported_by or "DISPATCH_CENTER",
                    None,
                    now_iso,
                    now_iso,
                    None,
                ),
            )
            conn.commit()
            logger.info(f"Created new incident {code} ({inc_id})")
            return cls.get_incident(inc_id)
        finally:
            conn.close()

    @classmethod
    def update_incident(cls, incident_id: str, data: IncidentUpdate) -> Optional[Dict[str, Any]]:
        existing = cls.get_incident(incident_id)
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
            cursor.execute(f"UPDATE incidents SET {', '.join(fields)} WHERE id = ?;", params)
            conn.commit()
            return cls.get_incident(existing["id"])
        finally:
            conn.close()

    @classmethod
    def resolve_incident(cls, incident_id: str) -> Optional[Dict[str, Any]]:
        existing = cls.get_incident(incident_id)
        if not existing:
            return None

        now_iso = datetime.utcnow().isoformat() + "Z"
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE incidents SET status = 'RESOLVED', updated_at = ?, resolved_at = ? WHERE id = ?;",
                (now_iso, now_iso, existing["id"]),
            )
            # Release assigned unit if any
            if existing.get("assigned_unit_id"):
                cursor.execute(
                    "UPDATE rescue_units SET status = 'AVAILABLE', current_incident_id = NULL, updated_at = ? WHERE id = ?;",
                    (now_iso, existing["assigned_unit_id"]),
                )
            conn.commit()
            return cls.get_incident(existing["id"])
        finally:
            conn.close()

    @classmethod
    def delete_incident(cls, incident_id: str) -> bool:
        existing = cls.get_incident(incident_id)
        if not existing:
            return False
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM incidents WHERE id = ?;", (existing["id"],))
            conn.commit()
            return True
        finally:
            conn.close()


incident_service = IncidentService()
