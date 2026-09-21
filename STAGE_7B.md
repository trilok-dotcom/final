# STAGE 7B: Automatic Rescue Unit Dispatch & AI Route Assignment

## Overview
Stage 7B implements a production-ready automatic emergency dispatch engine that selects the nearest suitable available rescue unit via Haversine distance, assigns the unit, changes unit status to `DISPATCHED`, generates internal AI emergency Dijkstra routes over the U-Net extracted road graph, persists dispatch records in SQLite, synchronizes mission state progression (`DISPATCHED` $\rightarrow$ `EN_ROUTE` $\rightarrow$ `ON_SCENE` $\rightarrow$ `COMPLETED`), and renders the active mission on Leaflet maps.

---

## 1. Database Architecture: `dispatches` Table

### Database File: `backend/resqroute.db`

#### Schema
- `id`: TEXT PRIMARY KEY (e.g., `disp-17f33226`)
- `incident_id`: TEXT NOT NULL (FOREIGN KEY $\rightarrow$ `incidents(id)`)
- `rescue_unit_id`: TEXT NOT NULL (FOREIGN KEY $\rightarrow$ `rescue_units(id)`)
- `status`: TEXT NOT NULL (`PENDING`, `DISPATCHED`, `EN_ROUTE`, `ON_SCENE`, `COMPLETED`, `CANCELLED`)
- `assigned_at`: TEXT ISO8601 Timestamp
- `dispatched_at`: TEXT ISO8601 Timestamp
- `en_route_at`: TEXT ISO8601 Timestamp
- `arrived_at`: TEXT ISO8601 Timestamp
- `completed_at`: TEXT ISO8601 Timestamp
- `cancelled_at`: TEXT ISO8601 Timestamp
- `route_id`: TEXT
- `distance_meters`: REAL DEFAULT 0.0
- `estimated_duration_seconds`: INTEGER DEFAULT 0
- `average_confidence`: REAL DEFAULT 1.0
- `risk_level`: TEXT DEFAULT 'low'
- `route_geometry_json`: TEXT JSON
- `route_steps_json`: TEXT JSON
- `created_at`: TEXT ISO8601 Timestamp
- `updated_at`: TEXT ISO8601 Timestamp

#### Indexes
- `idx_dispatches_incident` ON `dispatches(incident_id)`
- `idx_dispatches_unit` ON `dispatches(rescue_unit_id)`
- `idx_dispatches_status` ON `dispatches(status)`
- `idx_dispatches_created` ON `dispatches(created_at)`

---

## 2. Response Type Matching & Automatic Unit Selection

### Incident Type to Unit Type Preference Hierarchy
- `MEDICAL`, `ACCIDENT` $\rightarrow$ `AMBULANCE`, `DISASTER_RESPONSE`
- `FIRE`, `HAZMAT` $\rightarrow$ `FIRE_TRUCK`, `RESCUE_TEAM`
- `COLLAPSED_BUILDING`, `EARTHQUAKE`, `FLOOD`, `LANDSLIDE`, `STORM`, `TSUNAMI` $\rightarrow$ `RESCUE_TEAM`, `DISASTER_RESPONSE`
- `MISSING_PERSON`, `OTHER` $\rightarrow$ `POLICE`, `RESCUE_TEAM`

### Selection Process
1. Query available rescue units (`status = 'AVAILABLE'`).
2. Filter units by preferred type match first.
3. Fallback to any available unit if no exact match exists.
4. Calculate Haversine geographic distance in meters to each candidate unit.
5. Select nearest unit and trigger internal AI Dijkstra route calculation.

---

## 3. Mission State Machine & Synchronization

### Allowed Dispatch Status Transitions
- `PENDING` $\rightarrow$ `DISPATCHED`
- `DISPATCHED` $\rightarrow$ `EN_ROUTE`
- `EN_ROUTE` $\rightarrow$ `ON_SCENE`
- `ON_SCENE` $\rightarrow$ `COMPLETED`
- `DISPATCHED` $\rightarrow$ `CANCELLED`
- `EN_ROUTE` $\rightarrow$ `CANCELLED`

### Synchronized Entity States
| Dispatch Status | Rescue Unit Status | Incident Status |
| :--- | :--- | :--- |
| `DISPATCHED` | `DISPATCHED` | `DISPATCHING` |
| `EN_ROUTE` | `EN_ROUTE` | `ACTIVE` |
| `ON_SCENE` | `ON_SCENE` | `ACTIVE` |
| `COMPLETED` | `AVAILABLE` (Released) | `RESOLVED` |
| `CANCELLED` | `AVAILABLE` (Released) | `REPORTED` |

---

## 4. API Endpoints

- `POST /api/dispatch/incident/{incident_id}` (and `/api/v1/dispatch/incident/{incident_id}`): Trigger automatic dispatch.
- `GET /api/dispatches` (and `/api/v1/dispatches`): List dispatches with optional query `?status=`.
- `GET /api/dispatches/{dispatch_id}` (and `/api/v1/dispatches/{dispatch_id}`): Retrieve single dispatch mission.
- `PATCH /api/dispatches/{dispatch_id}/status` (and `/api/v1/dispatches/{dispatch_id}/status`): Advance mission status.
