# STAGE 7C: Live Emergency Mission Tracking & Real-Time Operations

## Overview
Stage 7C introduces real-time mission telemetry tracking, FastAPI WebSockets (`/api/ws/missions`), 5-second REST polling fallback, live AI route movement simulation along stored U-Net Dijkstra polyline coordinates, compass heading calculation, emergency progress indicators, and interactive Leaflet map marker rendering.

---

## 1. Database Architecture: `mission_updates` Table

### Database File: `backend/resqroute.db`

#### Schema
- `id`: TEXT PRIMARY KEY (e.g., `upd-1a2b3c4d`)
- `dispatch_id`: TEXT NOT NULL (FOREIGN KEY $\rightarrow$ `dispatches(id)`)
- `rescue_unit_id`: TEXT NOT NULL (FOREIGN KEY $\rightarrow$ `rescue_units(id)`)
- `incident_id`: TEXT NOT NULL (FOREIGN KEY $\rightarrow$ `incidents(id)`)
- `latitude`: REAL NOT NULL
- `longitude`: REAL NOT NULL
- `status`: TEXT NOT NULL
- `distance_remaining_meters`: REAL DEFAULT 0.0
- `eta_seconds`: INTEGER DEFAULT 0
- `progress_percent`: REAL DEFAULT 0.0
- `speed_kmh`: REAL DEFAULT 0.0
- `heading_degrees`: REAL DEFAULT 0.0
- `timestamp`: TEXT ISO8601 Timestamp

#### Indexes
- `idx_mission_updates_dispatch` ON `mission_updates(dispatch_id)`
- `idx_mission_updates_unit` ON `mission_updates(rescue_unit_id)`
- `idx_mission_updates_timestamp` ON `mission_updates(timestamp)`

---

## 2. Real-Time Telemetry & WebSocket Architecture

### WebSocket Endpoint: `WS /api/ws/missions`
- Connects clients to live mission event stream.
- Event Broadcast Payload:
  ```json
  {
    "type": "MISSION_UPDATE",
    "dispatch_id": "disp-17f33226",
    "unit_id": "unit-1",
    "status": "EN_ROUTE",
    "location": { "lat": 12.9751, "lng": 77.5904 },
    "speed_kmh": 45.0,
    "heading_degrees": 135.0,
    "distance_remaining_meters": 1850.4,
    "eta_seconds": 148,
    "progress_percent": 44.5,
    "timestamp": "2026-08-30T21:45:00Z"
  }
  ```

### REST Fallback
If the WebSocket stream is disconnected, the frontend automatically falls back to polling `GET /api/dispatches/{dispatch_id}/live` every 5 seconds until WebSocket reconnects.

---

## 3. Movement Simulation Engine

- Endpoint: `POST /api/dispatches/{dispatch_id}/simulate`
- Stop Endpoint: `POST /api/dispatches/{dispatch_id}/simulation/stop`
- Behavior: Spawns an async `asyncio.create_task` stepping the unit along stored `route_geometry_json` polyline coordinates, updating distance remaining, progress %, ETA, and heading degrees at 1.0-second intervals.
