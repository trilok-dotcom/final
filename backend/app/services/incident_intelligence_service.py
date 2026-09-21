import math
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.services.incident_service import incident_service
from app.services.rescue_unit_service import rescue_unit_service
from app.services.emergency_routing_service import emergency_routing_service, haversine_distance_km
from app.models.incident_intelligence import PriorityLevel, UrgencyLevel, IntelligenceRiskLevel
from app.utils.logging import get_logger

logger = get_logger("app.services.incident_intelligence_service")

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

# Factor Raw Score Mappings
SEVERITY_SCORES: Dict[str, float] = {
    "CRITICAL": 100.0,
    "HIGH": 75.0,
    "MEDIUM": 50.0,
    "MODERATE": 50.0,
    "LOW": 25.0,
}

INCIDENT_TYPE_SCORES: Dict[str, float] = {
    "COLLAPSED_BUILDING": 95.0,
    "EARTHQUAKE": 95.0,
    "HAZMAT": 90.0,
    "FIRE": 85.0,
    "FLOOD": 85.0,
    "TSUNAMI": 90.0,
    "MEDICAL": 75.0,
    "ACCIDENT": 75.0,
    "LANDSLIDE": 75.0,
    "STORM": 65.0,
    "MISSING_PERSON": 55.0,
    "OTHER": 40.0,
}

TIME_SENSITIVITY_SCORES: Dict[str, float] = {
    "MEDICAL": 95.0,
    "FIRE": 95.0,
    "COLLAPSED_BUILDING": 95.0,
    "HAZMAT": 90.0,
    "ACCIDENT": 80.0,
    "EARTHQUAKE": 85.0,
    "FLOOD": 80.0,
    "STORM": 65.0,
    "LANDSLIDE": 65.0,
    "MISSING_PERSON": 50.0,
    "OTHER": 35.0,
}


class IncidentIntelligenceService:
    @classmethod
    def analyze_incident(cls, incident_id: str) -> Dict[str, Any]:
        """
        Analyze target emergency incident using deterministic weighted scoring engine.
        Returns priority score (0-100), priority level, risk level, urgency, recommended resources,
        factor breakdown, and human-readable explanation.
        """
        # 1. Fetch incident
        incident = incident_service.get_incident(incident_id)
        if not incident:
            raise ValueError(f"Emergency incident '{incident_id}' not found.")

        inc_code = incident.get("incident_code") or incident.get("code") or "INC-000"
        inc_type = (incident.get("incident_type") or incident.get("type") or "OTHER").upper()
        severity = (incident.get("severity") or "LOW").upper()
        inc_lat = float(incident["latitude"])
        inc_lng = float(incident["longitude"])

        # 2. Factor 1: Severity Score
        sev_raw = SEVERITY_SCORES.get(severity, 25.0)
        sev_weighted = round(sev_raw * WEIGHT_SEVERITY, 2)
        sev_factor = {
            "name": "Severity Triage",
            "raw_score": sev_raw,
            "weight": WEIGHT_SEVERITY,
            "weighted_score": sev_weighted,
            "reason": f"Incident triage severity is classified as {severity}",
        }

        # 3. Factor 2: Incident Type Hazard Profile
        type_raw = INCIDENT_TYPE_SCORES.get(inc_type, 40.0)
        type_weighted = round(type_raw * WEIGHT_INCIDENT_TYPE, 2)
        type_factor = {
            "name": "Incident Type Risk",
            "raw_score": type_raw,
            "weight": WEIGHT_INCIDENT_TYPE,
            "weighted_score": type_weighted,
            "reason": f"{inc_type.replace('_', ' ')} incident category hazard profile",
        }

        # 4. Factor 3: Time Sensitivity Urgency
        time_raw = TIME_SENSITIVITY_SCORES.get(inc_type, 35.0)
        if severity == "CRITICAL":
            time_raw = min(100.0, time_raw + 10.0)
        time_weighted = round(time_raw * WEIGHT_TIME_SENSITIVITY, 2)
        time_factor = {
            "name": "Time Sensitivity",
            "raw_score": time_raw,
            "weight": WEIGHT_TIME_SENSITIVITY,
            "weighted_score": time_weighted,
            "reason": f"Golden-hour emergency response tolerance for {inc_type.replace('_', ' ')}",
        }

        # 5. Factor 4: Location Risk & Proximity Concentration
        all_incidents = incident_service.list_incidents()
        nearby_count = 0
        for other in all_incidents:
            if other.get("id") != incident.get("id") and other.get("status") in ("REPORTED", "ACTIVE", "DISPATCHING"):
                o_lat = float(other["latitude"])
                o_lng = float(other["longitude"])
                if haversine_distance_km(inc_lat, inc_lng, o_lat, o_lng) <= 3.0:
                    nearby_count += 1

        is_bounds = emergency_routing_service.geo.is_within_bounds(inc_lat, inc_lng)
        loc_raw = 50.0
        if is_bounds:
            loc_raw += 15.0  # Georeferenced satellite zone active
        if nearby_count > 0:
            loc_raw += min(30.0, nearby_count * 15.0)  # Multi-incident concentration penalty
        loc_raw = min(100.0, loc_raw)
        loc_weighted = round(loc_raw * WEIGHT_LOCATION_RISK, 2)
        loc_factor = {
            "name": "Location Risk",
            "raw_score": loc_raw,
            "weight": WEIGHT_LOCATION_RISK,
            "weighted_score": loc_weighted,
            "reason": f"{nearby_count} active nearby incidents within 3km sector" if nearby_count > 0 else "Baseline geographic location profile",
        }

        # 6. Factor 5: Response Difficulty & Unit Proximity
        avail_units = rescue_unit_service.list_rescue_units(status="AVAILABLE")
        nearest_dist_km = 999.0
        if avail_units:
            for u in avail_units:
                u_lat = float(u["latitude"])
                u_lng = float(u["longitude"])
                d = haversine_distance_km(u_lat, u_lng, inc_lat, inc_lng)
                if d < nearest_dist_km:
                    nearest_dist_km = d

        diff_raw = 40.0
        if nearest_dist_km > 5.0 and nearest_dist_km < 900.0:
            diff_raw += 30.0  # Extended unit transit distance
        elif not avail_units:
            diff_raw += 50.0  # No units currently on standby

        diff_raw = min(100.0, diff_raw)
        diff_weighted = round(diff_raw * WEIGHT_RESPONSE_DIFFICULTY, 2)
        diff_factor = {
            "name": "Response Difficulty",
            "raw_score": diff_raw,
            "weight": WEIGHT_RESPONSE_DIFFICULTY,
            "weighted_score": diff_weighted,
            "reason": f"Nearest unit is {nearest_dist_km:.1f}km away" if nearest_dist_km < 900.0 else "No units available on standby",
        }

        # 7. Final Priority Score Calculation (0 - 100)
        total_score = round(sev_weighted + type_weighted + time_weighted + loc_weighted + diff_weighted, 1)
        total_score = min(100.0, max(0.0, total_score))

        # 8. Classifications
        if total_score >= THRESHOLD_CRITICAL:
            priority = PriorityLevel.CRITICAL.value
            urgency = UrgencyLevel.IMMEDIATE.value
            risk_level = IntelligenceRiskLevel.CRITICAL.value if inc_type in ("COLLAPSED_BUILDING", "HAZMAT", "FIRE", "EARTHQUAKE") else IntelligenceRiskLevel.HIGH.value
        elif total_score >= THRESHOLD_HIGH:
            priority = PriorityLevel.HIGH.value
            urgency = UrgencyLevel.URGENT.value
            risk_level = IntelligenceRiskLevel.HIGH.value if inc_type in ("FIRE", "HAZMAT", "FLOOD") else IntelligenceRiskLevel.MODERATE.value
        elif total_score >= THRESHOLD_MEDIUM:
            priority = PriorityLevel.MEDIUM.value
            urgency = UrgencyLevel.PRIORITY.value
            risk_level = IntelligenceRiskLevel.MODERATE.value
        else:
            priority = PriorityLevel.LOW.value
            urgency = UrgencyLevel.ROUTINE.value
            risk_level = IntelligenceRiskLevel.LOW.value

        # 9. Resource Recommendations
        rec_resources = cls._recommend_resources(inc_type, severity, total_score)

        # 10. AI Explanation Summary
        rec_str = ", ".join(f"{r['quantity']}x {r['unit_type']}" for r in rec_resources)
        explanation = (
            f"Incident {inc_code} priority classified as {priority} (Score: {total_score}/100) "
            f"with {urgency} response urgency. The event is a {severity} severity {inc_type.replace('_', ' ')} incident. "
            f"Recommended deployment includes {rec_str}."
        )

        now_iso = datetime.utcnow().isoformat() + "Z"

        return {
            "incident_id": incident["id"],
            "incident_code": inc_code,
            "priority_score": total_score,
            "priority": priority,
            "risk_level": risk_level,
            "urgency": urgency,
            "recommended_resources": rec_resources,
            "factors": [sev_factor, type_factor, time_factor, loc_factor, diff_factor],
            "explanation": explanation,
            "analyzed_at": now_iso,
        }

    @staticmethod
    def _recommend_resources(inc_type: str, severity: str, score: float) -> List[Dict[str, Any]]:
        """Structure required rescue unit recommendations based on incident type and priority score."""
        recs = []
        if inc_type == "FIRE":
            recs.append({"unit_type": "FIRE_TRUCK", "quantity": 2 if score >= 80 else 1, "reason": "Active structural fire suppression and containment"})
            recs.append({"unit_type": "AMBULANCE", "quantity": 1, "reason": "Emergency medical and smoke inhalation triage"})
        elif inc_type == "HAZMAT":
            recs.append({"unit_type": "FIRE_TRUCK", "quantity": 1, "reason": "Hazmat suppression and perimeter containment"})
            recs.append({"unit_type": "RESCUE_TEAM", "quantity": 1, "reason": "Chemical decontamination and extraction"})
        elif inc_type == "COLLAPSED_BUILDING":
            recs.append({"unit_type": "RESCUE_TEAM", "quantity": 2 if score >= 80 else 1, "reason": "Urban search & rescue structural shoring"})
            recs.append({"unit_type": "AMBULANCE", "quantity": 2, "reason": "Trauma patient stabilization and transport"})
        elif inc_type == "EARTHQUAKE":
            recs.append({"unit_type": "RESCUE_TEAM", "quantity": 2, "reason": "Disaster search and casualty extraction"})
            recs.append({"unit_type": "AMBULANCE", "quantity": 2, "reason": "Emergency trauma field medical station"})
            recs.append({"unit_type": "POLICE", "quantity": 1, "reason": "Disaster perimeter security and traffic routing"})
        elif inc_type == "FLOOD":
            recs.append({"unit_type": "RESCUE_TEAM", "quantity": 1, "reason": "Water rescue and swiftwater evacuation squad"})
            recs.append({"unit_type": "AMBULANCE", "quantity": 1, "reason": "Hypothermia and emergency medical care"})
        elif inc_type == "ACCIDENT":
            recs.append({"unit_type": "AMBULANCE", "quantity": 1, "reason": "Vehicle collision injury patient transport"})
            recs.append({"unit_type": "POLICE", "quantity": 1, "reason": "Traffic control and scene investigation"})
        elif inc_type == "MISSING_PERSON":
            recs.append({"unit_type": "POLICE", "quantity": 1, "reason": "Search and locate search team"})
            recs.append({"unit_type": "RESCUE_TEAM", "quantity": 1, "reason": "Terrain search and rescue squad"})
        else:
            recs.append({"unit_type": "AMBULANCE", "quantity": 1, "reason": "Standard emergency medical response"})

        return recs


incident_intelligence_service = IncidentIntelligenceService()
