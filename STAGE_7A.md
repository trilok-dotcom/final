# STAGE 7A: Emergency Incident + Rescue Unit Foundation

## Overview
Stage 7A establishes the backend and frontend foundation for managing emergency incidents and rescue units, incorporating SQLite persistence, REST API endpoints, status workflows, and interactive map marker representations.

---

## 1. Database Architecture & Models

### Database File: `backend/resqroute.db`

#### Incidents Table (`incidents`)
- `id`: TEXT PRIMARY KEY
- `incident_code`: TEXT UNIQUE NOT NULL (e.g., `INC-2026-0001`)
- `incident_type`: TEXT NOT NULL (`FIRE`, `MEDICAL`, `ACCIDENT`, `FLOOD`, `COLLAPSED_BUILDING`, `EARTHQUAKE`, `MISSING_PERSON`, `HAZMAT`, `OTHER`)
- `severity`: TEXT NOT NULL (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- `status`: TEXT NOT NULL (`REPORTED`, `VERIFIED`, `DISPATCHING`, `ACTIVE`, `RESOLVED`, `CANCELLED`)
- `latitude`: REAL NOT NULL ($-90.0$ to $90.0$)
- `longitude`: REAL NOT NULL ($-180.0$ to $180.0$)
- `location_name`: TEXT
- `description`: TEXT
- `reported_by`: TEXT
- `assigned_unit_id`: TEXT (FOREIGN KEY referencing `rescue_units(id)`)
- `created_at`: TEXT ISO8601 Timestamp
- `updated_at`: TEXT ISO8601 Timestamp
- `resolved_at`: TEXT ISO8601 Timestamp

#### Rescue Units Table (`rescue_units`)
- `id`: TEXT PRIMARY KEY
- `unit_code`: TEXT UNIQUE NOT NULL (e.g., `AMB-01`)
- `unit_type`: TEXT NOT NULL (`AMBULANCE`, `FIRE_TRUCK`, `POLICE`, `RESCUE_TEAM`, `DISASTER_RESPONSE`)
- `status`: TEXT NOT NULL (`AVAILABLE`, `DISPATCHED`, `EN_ROUTE`, `ON_SCENE`, `RETURNING`, `OFFLINE`)
- `latitude`: REAL NOT NULL ($-90.0$ to $90.0$)
- `longitude`: REAL NOT NULL ($-180.0$ to $180.0$)
- `name`: TEXT NOT NULL
- `crew_size`: INTEGER NOT NULL DEFAULT 1
- `capabilities`: TEXT JSON Array (e.g., `["medical", "first_aid", "patient_transport"]`)
- `current_incident_id`: TEXT (FOREIGN KEY referencing `incidents(id)`)
- `created_at`: TEXT ISO8601 Timestamp
- `updated_at`: TEXT ISO8601 Timestamp

#### Database Indexes
- `idx_incidents_status` ON `incidents(status)`
- `idx_incidents_severity` ON `incidents(severity)`
- `idx_incidents_created_at` ON `incidents(created_at)`
- `idx_incidents_type` ON `incidents(incident_type)`
- `idx_rescue_units_status` ON `rescue_units(status)`
- `idx_rescue_units_type` ON `rescue_units(unit_type)`

---

## 2. API Endpoints

### Emergency Incidents API
- `POST /api/incidents`: Create new incident (HTTP 201 Created)
- `GET /api/incidents`: List incidents with optional query filters `?status=`, `?severity=`, `?incident_type=`
- `GET /api/incidents/{incident_id}`: Retrieve single incident by ID or `incident_code`
- `PATCH /api/incidents/{incident_id}`: Update incident fields
- `DELETE /api/incidents/{incident_id}`: Delete incident (HTTP 204)
- `POST /api/incidents/{incident_id}/resolve`: Resolve incident and update `resolved_at`

### Rescue Units API
- `POST /api/rescue-units`: Create new rescue unit (HTTP 201 Created, HTTP 409 Conflict if duplicate `unit_code`)
- `GET /api/rescue-units`: List rescue units with optional query filters `?status=`, `?unit_type=`
- `GET /api/rescue-units/{unit_id}`: Retrieve single rescue unit by ID or `unit_code`
- `PATCH /api/rescue-units/{unit_id}`: Update rescue unit details
- `PATCH /api/rescue-units/{unit_id}/status`: Update status (`AVAILABLE`, `DISPATCHED`, `EN_ROUTE`, `ON_SCENE`, `RETURNING`, `OFFLINE`)
- `DELETE /api/rescue-units/{unit_id}`: Delete rescue unit (HTTP 204)

---

## 3. Future Stage 7B Integration Points
- **Automatic Dispatch Engine**: Stage 7B will select the nearest `AVAILABLE` unit based on Haversine / AI graph distance and trigger automatic dispatch assignment (`unit.status = 'DISPATCHED'`, `incident.status = 'DISPATCHING'`).
- **AI Route Assignment**: Stage 7B will automatically call `calculateAIRoute()` between assigned rescue unit coordinates and target emergency incident coordinates.
