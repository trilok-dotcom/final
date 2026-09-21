# STAGE 8A: AI Incident Intelligence & Priority Engine

## Overview
Stage 8A introduces a transparent, deterministic AI-assisted incident scoring engine (`incident_intelligence_service.py`) that analyzes emergency incidents to produce:
1. Priority Score (0–100)
2. Priority Classification (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`)
3. Emergency Risk Level (`CRITICAL`, `HIGH`, `MODERATE`, `LOW`)
4. Response Urgency (`IMMEDIATE`, `URGENT`, `PRIORITY`, `ROUTINE`)
5. Required Resource Recommendations (`unit_type`, `quantity`, `reason`)
6. 5-Factor Contributing Factors Breakdown
7. Human-Readable AI Natural Language Explanation

---

## 1. Centralized Weight Configuration

```python
# Centralized Factor Weights (Sum = 1.0)
WEIGHT_SEVERITY = 0.30
WEIGHT_INCIDENT_TYPE = 0.25
WEIGHT_TIME_SENSITIVITY = 0.15
WEIGHT_LOCATION_RISK = 0.15
WEIGHT_RESPONSE_DIFFICULTY = 0.15

# Priority Score Classification Thresholds
THRESHOLD_CRITICAL = 80.0
THRESHOLD_HIGH = 65.0
THRESHOLD_MEDIUM = 40.0
```

---

## 2. API Endpoints

- `POST /api/incidents/{incident_id}/analyze`
- `GET /api/incidents/{incident_id}/intelligence`
- `POST /api/v1/incidents/{incident_id}/analyze`
- `GET /api/v1/incidents/{incident_id}/intelligence`

---

## 3. Sample Response Payload

```json
{
  "incident_id": "inc-4e623b33",
  "incident_code": "INC-2026-0001",
  "priority_score": 89.0,
  "priority": "CRITICAL",
  "risk_level": "CRITICAL",
  "urgency": "IMMEDIATE",
  "recommended_resources": [
    {
      "unit_type": "RESCUE_TEAM",
      "quantity": 2,
      "reason": "Urban search & rescue structural shoring"
    },
    {
      "unit_type": "AMBULANCE",
      "quantity": 2,
      "reason": "Trauma patient stabilization and transport"
    }
  ],
  "factors": [
    {
      "name": "Severity Triage",
      "raw_score": 100.0,
      "weight": 0.30,
      "weighted_score": 30.0,
      "reason": "Incident triage severity is classified as CRITICAL"
    },
    {
      "name": "Incident Type Risk",
      "raw_score": 95.0,
      "weight": 0.25,
      "weighted_score": 23.75,
      "reason": "COLLAPSED BUILDING incident category hazard profile"
    },
    {
      "name": "Time Sensitivity",
      "raw_score": 100.0,
      "weight": 0.15,
      "weighted_score": 15.0,
      "reason": "Golden-hour emergency response tolerance for COLLAPSED BUILDING"
    },
    {
      "name": "Location Risk",
      "raw_score": 65.0,
      "weight": 0.15,
      "weighted_score": 9.75,
      "reason": "Baseline geographic location profile"
    },
    {
      "name": "Response Difficulty",
      "raw_score": 70.0,
      "weight": 0.15,
      "weighted_score": 10.5,
      "reason": "Nearest unit is 1.5km away"
    }
  ],
  "explanation": "Incident INC-2026-0001 priority classified as CRITICAL (Score: 89.0/100) with IMMEDIATE response urgency. The event is a CRITICAL severity COLLAPSED BUILDING incident. Recommended deployment includes 2x RESCUE_TEAM, 2x AMBULANCE.",
  "analyzed_at": "2026-08-30T22:04:05Z"
}
```
