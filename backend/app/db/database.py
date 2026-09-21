import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.utils.logging import get_logger

logger = get_logger("app.db.database")

DB_FILE = Path(__file__).resolve().parent.parent.parent / "resqroute.db"


def get_db_connection() -> sqlite3.Connection:
    """Create and return a thread-safe SQLite database connection."""
    conn = sqlite3.connect(str(DB_FILE), timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Initialize database tables, indexes, and initial demo seed records."""
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # 1. Incidents Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                incident_code TEXT UNIQUE NOT NULL,
                incident_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                location_name TEXT,
                description TEXT,
                reported_by TEXT DEFAULT 'DISPATCH_CENTER',
                assigned_unit_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved_at TEXT,
                FOREIGN KEY (assigned_unit_id) REFERENCES rescue_units(id) ON DELETE SET NULL
            );
            """
        )

        # 2. Rescue Units Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rescue_units (
                id TEXT PRIMARY KEY,
                unit_code TEXT UNIQUE NOT NULL,
                unit_type TEXT NOT NULL,
                status TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                name TEXT NOT NULL,
                crew_size INTEGER NOT NULL DEFAULT 1,
                capabilities TEXT NOT NULL,
                current_incident_id TEXT,
                speed_kmh REAL DEFAULT 0.0,
                heading_degrees REAL DEFAULT 0.0,
                last_updated TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (current_incident_id) REFERENCES incidents(id) ON DELETE SET NULL
            );
            """
        )

        # Ensure speed_kmh, heading_degrees, last_updated exist if table was previously created
        try:
            cursor.execute("ALTER TABLE rescue_units ADD COLUMN speed_kmh REAL DEFAULT 0.0;")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE rescue_units ADD COLUMN heading_degrees REAL DEFAULT 0.0;")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE rescue_units ADD COLUMN last_updated TEXT;")
        except Exception:
            pass

        # 3. Dispatches / Missions Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dispatches (
                id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                rescue_unit_id TEXT NOT NULL,
                status TEXT NOT NULL,
                assigned_at TEXT NOT NULL,
                dispatched_at TEXT,
                en_route_at TEXT,
                arrived_at TEXT,
                completed_at TEXT,
                cancelled_at TEXT,
                route_id TEXT,
                distance_meters REAL DEFAULT 0.0,
                estimated_duration_seconds INTEGER DEFAULT 0,
                average_confidence REAL DEFAULT 1.0,
                risk_level TEXT DEFAULT 'low',
                route_geometry_json TEXT,
                route_steps_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE,
                FOREIGN KEY (rescue_unit_id) REFERENCES rescue_units(id) ON DELETE CASCADE
            );
            """
        )

        # 4. Mission Telemetry Updates Table (Stage 7C)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS mission_updates (
                id TEXT PRIMARY KEY,
                dispatch_id TEXT NOT NULL,
                rescue_unit_id TEXT NOT NULL,
                incident_id TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                status TEXT NOT NULL,
                distance_remaining_meters REAL DEFAULT 0.0,
                eta_seconds INTEGER DEFAULT 0,
                progress_percent REAL DEFAULT 0.0,
                speed_kmh REAL DEFAULT 0.0,
                heading_degrees REAL DEFAULT 0.0,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (dispatch_id) REFERENCES dispatches(id) ON DELETE CASCADE,
                FOREIGN KEY (rescue_unit_id) REFERENCES rescue_units(id) ON DELETE CASCADE,
                FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE
            );
            """
        )

        # 5. Resource Assignments Table (Stage 8B)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS resource_assignments (
                id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                dispatch_id TEXT,
                rescue_unit_id TEXT NOT NULL,
                unit_type TEXT NOT NULL,
                optimization_score REAL NOT NULL,
                distance_meters REAL NOT NULL,
                estimated_duration_seconds INTEGER NOT NULL,
                average_confidence REAL NOT NULL,
                risk_level TEXT NOT NULL,
                suitability_score REAL NOT NULL,
                availability_score REAL NOT NULL,
                eta_score REAL NOT NULL,
                route_score REAL NOT NULL,
                capability_score REAL NOT NULL,
                selection_reason TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE,
                FOREIGN KEY (rescue_unit_id) REFERENCES rescue_units(id) ON DELETE CASCADE
            );
            """
        )

        # 6. Routes Table (Stage 8C Route Versioning)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS routes (
                id TEXT PRIMARY KEY,
                dispatch_id TEXT NOT NULL,
                route_type TEXT NOT NULL,
                status TEXT NOT NULL,
                distance_meters REAL NOT NULL,
                estimated_duration_seconds INTEGER NOT NULL,
                average_confidence REAL NOT NULL,
                risk_level TEXT NOT NULL,
                health_score REAL DEFAULT 0.0,
                route_geometry_json TEXT NOT NULL,
                route_steps_json TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                archived_at TEXT,
                FOREIGN KEY (dispatch_id) REFERENCES dispatches(id) ON DELETE CASCADE
            );
            """
        )

        # 7. Route Evaluations Table (Stage 8C)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS route_evaluations (
                id TEXT PRIMARY KEY,
                dispatch_id TEXT NOT NULL,
                evaluation_type TEXT NOT NULL,
                current_route_health TEXT NOT NULL,
                current_confidence REAL NOT NULL,
                current_risk_level TEXT NOT NULL,
                current_eta_seconds INTEGER NOT NULL,
                alternative_route_count INTEGER DEFAULT 0,
                recommended_route_id TEXT,
                decision TEXT NOT NULL,
                reason_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (dispatch_id) REFERENCES dispatches(id) ON DELETE CASCADE
            );
            """
        )

        # 8. Reroute Events Table (Stage 8C)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reroute_events (
                id TEXT PRIMARY KEY,
                dispatch_id TEXT NOT NULL,
                previous_route_id TEXT NOT NULL,
                new_route_id TEXT NOT NULL,
                trigger TEXT NOT NULL,
                reason TEXT NOT NULL,
                old_distance_meters REAL NOT NULL,
                new_distance_meters REAL NOT NULL,
                old_eta_seconds INTEGER NOT NULL,
                new_eta_seconds INTEGER NOT NULL,
                old_confidence REAL NOT NULL,
                new_confidence REAL NOT NULL,
                old_risk_level TEXT NOT NULL,
                new_risk_level TEXT NOT NULL,
                approved_by TEXT DEFAULT 'DISPATCH_OPERATOR',
                approved_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (dispatch_id) REFERENCES dispatches(id) ON DELETE CASCADE
            );
            """
        )

        # 9. Command Center Alerts Table (Stage 9A)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS command_center_alerts (
                id TEXT PRIMARY KEY,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                incident_id TEXT,
                dispatch_id TEXT,
                unit_id TEXT,
                acknowledged INTEGER DEFAULT 0,
                acknowledged_by TEXT,
                acknowledged_at TEXT,
                created_at TEXT NOT NULL
            );
            """
        )

        # 10. Simulation Sessions & Events Tables (Stage 9B)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS simulation_sessions (
                id TEXT PRIMARY KEY,
                scenario_type TEXT NOT NULL,
                scenario_name TEXT NOT NULL,
                seed INTEGER NOT NULL,
                scale TEXT NOT NULL,
                status TEXT NOT NULL,
                simulation_time INTEGER DEFAULT 0,
                speed INTEGER DEFAULT 1,
                started_at TEXT,
                paused_at TEXT,
                completed_at TEXT,
                stopped_at TEXT,
                bounds_json TEXT,
                summary_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS simulation_events (
                id TEXT PRIMARY KEY,
                simulation_session_id TEXT NOT NULL,
                simulated_time INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                data_json TEXT,
                status TEXT DEFAULT 'PENDING',
                executed_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (simulation_session_id) REFERENCES simulation_sessions(id) ON DELETE CASCADE
            );
            """
        )

        # 11. Evaluation Tables (Stage 10)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluation_runs (
                id TEXT PRIMARY KEY,
                evaluation_type TEXT NOT NULL,
                dataset_version TEXT,
                model_version TEXT,
                simulation_id TEXT,
                baseline_type TEXT,
                sample_count INTEGER DEFAULT 0,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL,
                metadata_json TEXT
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluation_metrics (
                id TEXT PRIMARY KEY,
                evaluation_run_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                unit TEXT,
                category TEXT NOT NULL,
                metadata_json TEXT,
                FOREIGN KEY (evaluation_run_id) REFERENCES evaluation_runs(id) ON DELETE CASCADE
            );
            """
        )

        # 12. Add simulation_session_id column to existing tables if missing
        for tbl in [
            "incidents",
            "rescue_units",
            "dispatches",
            "mission_updates",
            "resource_assignments",
            "routes",
            "route_evaluations",
            "reroute_events",
            "command_center_alerts",
        ]:
            try:
                cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN simulation_session_id TEXT;")
            except Exception:
                pass

        # 13. Create Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_type ON incidents(incident_type);")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rescue_units_status ON rescue_units(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rescue_units_type ON rescue_units(unit_type);")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dispatches_incident ON dispatches(incident_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dispatches_unit ON dispatches(rescue_unit_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dispatches_status ON dispatches(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dispatches_created ON dispatches(created_at);")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mission_updates_dispatch ON mission_updates(dispatch_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mission_updates_unit ON mission_updates(rescue_unit_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mission_updates_timestamp ON mission_updates(timestamp);")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_resource_assignments_incident ON resource_assignments(incident_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_resource_assignments_unit ON resource_assignments(rescue_unit_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_resource_assignments_status ON resource_assignments(status);")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_routes_dispatch ON routes(dispatch_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_routes_status ON routes(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_route_evaluations_dispatch ON route_evaluations(dispatch_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_route_evaluations_created ON route_evaluations(created_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reroute_events_dispatch ON reroute_events(dispatch_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reroute_events_created ON reroute_events(created_at);")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cc_alerts_dispatch ON command_center_alerts(dispatch_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cc_alerts_incident ON command_center_alerts(incident_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cc_alerts_acknowledged ON command_center_alerts(acknowledged);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cc_alerts_created ON command_center_alerts(created_at);")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sim_sessions_status ON simulation_sessions(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sim_events_session ON simulation_events(simulation_session_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_sim ON incidents(simulation_session_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_units_sim ON rescue_units(simulation_session_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dispatches_sim ON dispatches(simulation_session_id);")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evaluation_runs_type ON evaluation_runs(evaluation_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evaluation_runs_created ON evaluation_runs(started_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evaluation_metrics_run ON evaluation_metrics(evaluation_run_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evaluation_metrics_name ON evaluation_metrics(metric_name);")

        conn.commit()
        logger.info("Database tables and indexes initialized successfully.")

        # 6. Seed initial demo data if empty
        _seed_demo_data(conn)

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise
    finally:
        conn.close()


def _seed_demo_data(conn: sqlite3.Connection) -> None:
    """Seed initial development demo incidents and rescue units if tables are empty."""
    cursor = conn.cursor()
    
    # Check if rescue units exist
    cursor.execute("SELECT COUNT(*) FROM rescue_units;")
    unit_count = cursor.fetchone()[0]

    now_iso = datetime.utcnow().isoformat() + "Z"

    if unit_count == 0:
        logger.info("Seeding initial demo rescue units...")
        demo_units = [
            ("unit-1", "AMB-01", "AMBULANCE", "AVAILABLE", 12.979766, 77.583438, "Central Ambulance 01", 3, json.dumps(["medical", "first_aid", "patient_transport"]), None, 0.0, 0.0, now_iso, now_iso, now_iso),
            ("unit-2", "AMB-02", "AMBULANCE", "EN_ROUTE", 12.979609, 77.582930, "Metro Ambulance 02", 3, json.dumps(["medical", "trauma_support"]), None, 45.0, 180.0, now_iso, now_iso, now_iso),
            ("unit-3", "FIRE-01", "FIRE_TRUCK", "AVAILABLE", 12.979766, 77.583438, "Squad Fire Engine 01", 5, json.dumps(["fire_suppression", "rescue", "hazmat"]), None, 0.0, 0.0, now_iso, now_iso, now_iso),
            ("unit-4", "POL-01", "POLICE", "AVAILABLE", 12.979609, 77.582930, "Rapid Police Unit 01", 2, json.dumps(["traffic_control", "perimeter_security"]), None, 0.0, 0.0, now_iso, now_iso, now_iso),
            ("unit-5", "RES-01", "RESCUE_TEAM", "ON_SCENE", 12.966602, 77.599961, "Urban Search & Rescue Team 01", 6, json.dumps(["search_rescue", "collapsed_structure", "first_aid"]), None, 0.0, 0.0, now_iso, now_iso, now_iso),
        ]
        cursor.executemany(
            """
            INSERT INTO rescue_units (id, unit_code, unit_type, status, latitude, longitude, name, crew_size, capabilities, current_incident_id, speed_kmh, heading_degrees, last_updated, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            demo_units,
        )
        conn.commit()

    # Check if incidents exist
    cursor.execute("SELECT COUNT(*) FROM incidents;")
    incident_count = cursor.fetchone()[0]

    if incident_count == 0:
        logger.info("Seeding initial demo emergency incidents...")
        demo_incidents = [
            ("inc-1", "INC-2026-0001", "FIRE", "CRITICAL", "ACTIVE", 12.9716, 77.5946, "Commercial Complex MG Road", "Large building fire reported on 3rd floor.", "DISPATCH_CENTER", None, now_iso, now_iso, None),
            ("inc-2", "INC-2026-0002", "MEDICAL", "HIGH", "REPORTED", 12.9780, 77.5850, "North Transit Terminal", "Multiple vehicle collision with injuries.", "DISPATCH_CENTER", None, now_iso, now_iso, None),
            ("inc-3", "INC-2026-0003", "FLOOD", "CRITICAL", "ACTIVE", 12.9666, 77.5999, "Sector 4 Coastal Zone", "Flash flood inundating road infrastructure.", "DISPATCH_CENTER", "unit-5", now_iso, now_iso, None),
        ]
        cursor.executemany(
            """
            INSERT INTO incidents (id, incident_code, incident_type, severity, status, latitude, longitude, location_name, description, reported_by, assigned_unit_id, created_at, updated_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            demo_incidents,
        )
        # Link unit-5 current_incident_id to inc-3
        cursor.execute("UPDATE rescue_units SET current_incident_id = 'inc-3' WHERE id = 'unit-5';")
        conn.commit()
