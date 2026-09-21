# RESQROUTE — STAGE 8B: AI RESOURCE OPTIMIZATION & MULTI-UNIT DISPATCH ENGINE

## Overview

Stage 8B introduces a route-aware **AI Resource Optimization & Multi-Unit Dispatch Engine** for RESQROUTE. Consuming Stage 8A AI Incident Intelligence recommendations (e.g. `2x RESCUE_TEAM`, `2x AMBULANCE`), the engine calculates candidate suitability scores using in-process U-Net Dijkstra routes (`emergency_routing_service.py`), ranks candidate rescue units without double-booking, manages unit availability/reservation states, provides explainable factor breakdowns, and enables operators to execute atomic multi-unit dispatches.

---

## 1. Candidate Suitability Score Formula

The candidate suitability score is evaluated on a normalized scale of 0 to 100:

$$\text{Optimization Score} = (\text{ETA Score} \times 0.30) + (\text{Route Safety} \times 0.20) + (\text{AI Confidence} \times 0.15) + (\text{Capability} \times 0.20) + (\text{Availability} \times 0.10) + (\text{Operational} \times 0.05)$$

### Factor Scoring Definitions

| Factor | Weight | Scoring Logic |
|---|---|---|
| **ETA Score** | `0.30` | $\max(0, 100 - (\text{ETA\_seconds} / 12))$ |
| **Route Safety** | `0.20` | `100.0` for `low` risk, `70.0` for `moderate` risk, `40.0` for `high` risk |
| **AI Confidence** | `0.15` | $\text{average\_confidence} \times 100.0$ |
| **Capability** | `0.20` | `100.0` if capabilities match or crew size $\ge 2$, else `80.0` |
| **Availability** | `0.10` | `100.0` for units on `AVAILABLE` standby |
| **Operational** | `0.05` | `90.0` default operational readiness baseline |

---

## 2. Resource & Reservation States

### Resource Optimization Statuses
- **`OPTIMAL`**: All requested resource counts satisfied with available candidates.
- **`PARTIAL`**: Partial resource count satisfied due to shortage.
- **`INSUFFICIENT_RESOURCES`**: No available units found for requested types.
- **`NO_SUITABLE_UNITS`**: Zero units on standby.
- **`CONFLICT`**: Unit reserved/dispatched concurrently by another incident.
- **`ALREADY_DISPATCHED`**: Incident already has active dispatches.

### Unit & Assignment States
- **`CANDIDATE`**: Unit evaluated during optimization.
- **`RECOMMENDED`**: Top candidate selected by AI optimizer.
- **`RESERVED`**: Unit temporarily locked for incident pending operator confirmation.
- **`DISPATCHED`**: Operator confirmed and mission assigned with AI route.

---

## 3. Database Schema

### `resource_assignments` Table
```sql
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
```

### Indexes
- `idx_resource_assignments_incident` on `resource_assignments(incident_id)`
- `idx_resource_assignments_unit` on `resource_assignments(rescue_unit_id)`
- `idx_resource_assignments_status` on `resource_assignments(status)`

---

## 4. API Endpoints

### 1. `POST /api/incidents/{incident_id}/optimize-resources`
- Calculates optimal multi-unit allocation plan consuming Stage 8A intelligence recommendations.
- Evaluates candidate units using in-process U-Net Dijkstra routes.
- Ranks candidates, reserves units in DB, and returns structured candidate breakdown.

### 2. `POST /api/incidents/{incident_id}/dispatch-optimized`
- Confirms operator action and atomically dispatches all reserved units.
- Creates individual Stage 7B dispatch records with AI routes and updates unit states to `DISPATCHED`.

---

## 5. Automated Verification Results

All 18 steps in `backend/test_stage_8b_resource_optimization.py` passed cleanly:

```
==================================================
  RESQROUTE — STAGE 8B: RESOURCE OPTIMIZATION TEST
==================================================
[1/18] Creating Collapsed Building CRITICAL test incident...
[2/18] Optimizing resources via POST /api/incidents/{id}/optimize-resources...
[3/18] Verifying Stage 8A recommendations consumed correctly...
[4/18] Verifying candidate units discovery...
[5/18] Verifying route-aware distance and duration metrics...
[6/18] Verifying candidate 6-factor optimization scores...
[7/18] Verifying candidate ranking and top unit selection...
[8/18] Verifying no duplicate unit selections...
[9/18] Verifying selected units reserved in database...
[10/18] Dispatching optimized plan via POST /api/incidents/{id}/dispatch-optimized...
[11/18] Verifying multiple dispatch records created...
[12/18] Verifying rescue units transitioned to DISPATCHED status...
[13/18] Testing optimization protection on already-dispatched incident...
[14/18] Testing resource shortage handling on concurrent incident...
[15/18] Testing invalid dispatch request when no reservation exists...
[16/18] Completing dispatches to release units...
[17/18] Verifying units released back to AVAILABLE status...
[18/18] Cleaning up test records...

============================================================
STAGE 8B RESOURCE OPTIMIZATION TESTS COMPLETED SUCCESSFULLY
============================================================
```

### Full System Regression Verification
- `test_stage_8b_resource_optimization.py`: 18/18 steps PASSED (100%)
- `test_stage_8a_incident_intelligence.py`: 15/15 steps PASSED (100%)
- `test_stage_7c_live_tracking.py`: 20/20 steps PASSED (100%)
- `test_stage_7b_dispatch.py`: 17/17 steps PASSED (100%)
- `test_stage_7a_incidents_units.py`: 17/17 steps PASSED (100%)
- `npx tsc -b`: 0 errors
- `npx oxlint`: 0 errors
- `npm run build`: Vite production bundle compiled in 1.63s
