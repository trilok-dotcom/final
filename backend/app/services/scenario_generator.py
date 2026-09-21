import json
import random
from typing import Dict, Any, List, Optional
from app.utils.logging import get_logger

logger = get_logger("app.services.scenario_generator")

DEFAULT_BOUNDS = {
    "north": 12.9800,
    "south": 12.9600,
    "west": 77.5800,
    "east": 77.6000,
}

SCENARIO_TEMPLATES = {
    "URBAN_EARTHQUAKE": {
        "name": "Urban Earthquake Response Exercise",
        "description": "Seismic event causing structural collapse, road blockages, gas leaks, and severe casualties.",
        "incident_pool": [
            ("COLLAPSED_BUILDING", "CRITICAL", "Commercial Complex Structural Collapse", "4-story building partially collapsed with trapped victims."),
            ("TRAPPED_PERSONS", "CRITICAL", "Residential Block Entrapment", "Multiple occupants trapped in damaged apartment complex."),
            ("MEDICAL", "HIGH", "Mass Casualty Triage Point", "Multiple injured citizens needing urgent stabilization."),
            ("ROAD_OBSTRUCTION", "HIGH", "Major Arterial Road Debris Obstruction", "Bridge approach blocked by fallen concrete structures."),
            ("FIRE", "CRITICAL", "Substation Transformer Fire", "Electrical transformer on fire following seismic tremor."),
            ("HAZMAT", "HIGH", "Chemical Storage Containment Breach", "Toxic chemical leak reported near industrial perimeter."),
            ("MEDICAL", "MEDIUM", "Clinic Emergency Triage Overflow", "Walking wounded seeking medical assistance at neighborhood center."),
            ("ACCIDENT", "HIGH", "Overpass Collapse Collision", "Vehicles crushed beneath collapsed road segment."),
        ],
    },
    "URBAN_FLOOD": {
        "name": "Flash Flood Operations Exercise",
        "description": "Severe inundation flooding low-lying urban areas, stranding citizens and submerging routes.",
        "incident_pool": [
            ("FLOOD", "CRITICAL", "Flash Flood Evacuation Emergency", "Rapidly rising water levels trapping residents on rooftops."),
            ("STRANDED_PERSONS", "CRITICAL", "Underpass Submerged Bus Rescue", "Passenger bus trapped in 2-meter deep underpass floodwaters."),
            ("MEDICAL", "HIGH", "Hypothermia & Water Injury Emergency", "Flood victims rescued needing urgent medical care."),
            ("ROAD_OBSTRUCTION", "HIGH", "Submerged Main Highway Access", "Primary emergency response route submerged under 1m water."),
            ("EVACUATION", "HIGH", "Hospital Ground Floor Inundation", "Critical care patients require emergency relocation."),
            ("FLOOD", "MEDIUM", "Residential Sector Inundation", "Rising water threatening residential neighborhood."),
            ("HAZMAT", "HIGH", "Submerged Fuel Station Leak", "Fuel spill detected from inundated underground storage tank."),
            ("MEDICAL", "MEDIUM", "Stranded Elderly Support Request", "Elderly residents requiring food, water, and medication delivery."),
        ],
    },
    "INDUSTRIAL_FIRE": {
        "name": "Industrial Chemical & Fire Exercise",
        "description": "Major chemical plant explosion triggering high-intensity industrial fire and toxic plume.",
        "incident_pool": [
            ("FIRE", "CRITICAL", "Chemical Refinery Tank Farm Fire", "High-intensity industrial chemical tank farm fire with explosion risk."),
            ("HAZMAT", "CRITICAL", "Toxic Chlorine Gas Leak", "Pressurized gas container rupture releasing toxic chemical cloud."),
            ("INJURED_WORKERS", "HIGH", "Industrial Plant Trauma Emergency", "Multiple workers injured in pressure vessel blast."),
            ("EXPLOSION_RISK", "CRITICAL", "Secondary Solvent Depot Threat", "Adjacent chemical storage tanks at risk of thermal BLEVE."),
            ("ROAD_OBSTRUCTION", "MEDIUM", "Industrial Corridor Road Blockage", "Debris from explosion blocking emergency vehicle access."),
            ("MEDICAL", "HIGH", "Chemical Burn & Inhalation Support", "Workers suffering from severe chemical burns and smoke inhalation."),
            ("FIRE", "HIGH", "Warehouse Structural Fire", "Adjacent storage facility ignited by flying embers."),
            ("EVACUATION", "MEDIUM", "Perimeter Zone Evacuation Order", "Need police and transport units to clear 500m danger radius."),
        ],
    },
    "MULTI_VEHICLE_ACCIDENT": {
        "name": "Multi-Vehicle Mass Casualty Exercise",
        "description": "Chain-reaction multi-vehicle collision involving tanker trucks and commuter transport.",
        "incident_pool": [
            ("ACCIDENT", "CRITICAL", "Multi-Vehicle Freeway Pileup", "12-vehicle collision involving tanker truck and passenger buses."),
            ("TRAPPED_PASSENGER", "CRITICAL", "Crushed Commuter Bus Entrapment", "Multiple passengers pinned inside overturned commuter vehicle."),
            ("VEHICLE_FIRE", "HIGH", "Tanker Truck Fuel Fire", "Ruptured diesel fuel tank ignited on highway median."),
            ("TRAFFIC_OBSTRUCTION", "HIGH", "Complete Highway Gridlock", "Wreckage completely blocking north and southbound carriageways."),
            ("MEDICAL", "HIGH", "High-Velocity Trauma Emergency", "Urgent stabilization required for multiple critical trauma cases."),
            ("HAZMAT", "MEDIUM", "Fuel Spill Containment Hazard", "3,000 liters of diesel leaking across highway asphalt."),
            ("MEDICAL", "MEDIUM", "Minor Injury Triage Station", "Non-critical passengers requiring medical evaluation."),
            ("ACCIDENT", "MEDIUM", "Secondary Rear-End Collision", "Secondary accident at tail of traffic queue."),
        ],
    },
    "CUSTOM": {
        "name": "Custom Disaster Operations Exercise",
        "description": "User-defined multi-incident disaster exercise.",
        "incident_pool": [
            ("FIRE", "CRITICAL", "Custom High-Severity Incident", "Simulated critical emergency incident."),
            ("MEDICAL", "HIGH", "Custom Urgent Response Request", "Simulated high-priority response request."),
            ("FLOOD", "HIGH", "Custom Infrastructure Impact", "Simulated environmental infrastructure incident."),
            ("ACCIDENT", "MEDIUM", "Custom Moderate Hazard Event", "Simulated moderate response incident."),
        ],
    },
}

SCALE_CONFIGS = {
    "SMALL": {"num_incidents": 4, "num_units": 5},
    "MEDIUM": {"num_incidents": 8, "num_units": 10},
    "LARGE": {"num_incidents": 15, "num_units": 20},
}


class ScenarioGenerator:
    """
    Deterministic Disaster Scenario Generator.
    Generates deterministic incidents, simulation rescue units, and timeline event queues.
    """

    @classmethod
    def generate_scenario(
        cls,
        scenario_type: str,
        scale: str = "MEDIUM",
        seed: int = 42,
        bounds: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        scenario_type = (scenario_type or "URBAN_EARTHQUAKE").upper()
        if scenario_type not in SCENARIO_TEMPLATES:
            scenario_type = "URBAN_EARTHQUAKE"

        scale = (scale or "MEDIUM").upper()
        if scale not in SCALE_CONFIGS:
            scale = "MEDIUM"

        bounds = bounds or DEFAULT_BOUNDS
        north = float(bounds.get("north", DEFAULT_BOUNDS["north"]))
        south = float(bounds.get("south", DEFAULT_BOUNDS["south"]))
        west = float(bounds.get("west", DEFAULT_BOUNDS["west"]))
        east = float(bounds.get("east", DEFAULT_BOUNDS["east"]))

        rng = random.Random(seed)

        template = SCENARIO_TEMPLATES[scenario_type]
        scale_cfg = SCALE_CONFIGS[scale]
        num_incidents = scale_cfg["num_incidents"]
        num_units = scale_cfg["num_units"]

        # 1. Generate Deterministic Incidents
        incidents = []
        pool = template["incident_pool"]
        for i in range(num_incidents):
            tpl = pool[i % len(pool)]
            inc_type, severity, title, desc = tpl

            # Generate deterministic coords inside bounds
            lat = round(rng.uniform(south, north), 6)
            lng = round(rng.uniform(west, east), 6)

            incidents.append({
                "incident_type": inc_type,
                "severity": severity,
                "title": f"{title} #{i+1}",
                "description": desc,
                "latitude": lat,
                "longitude": lng,
                "location_name": f"Simulated Area Sector-{i+1}",
                "victim_estimate": rng.randint(2, 25) if severity in ("CRITICAL", "HIGH") else rng.randint(1, 5),
            })

        # 2. Generate Deterministic Simulation Rescue Fleet
        unit_types = ["AMBULANCE", "FIRE_TRUCK", "HAZMAT", "RESCUE_BOAT", "HELICOPTER"]
        units = []
        for u in range(num_units):
            utype = unit_types[u % len(unit_types)]
            lat = round(rng.uniform(south, north), 6)
            lng = round(rng.uniform(west, east), 6)
            code = f"SIM-{utype[:3]}-{u+1:02d}"
            name = f"Simulated {utype.replace('_', ' ').title()} Unit {u+1:02d}"

            caps = ["first_aid"]
            if utype == "AMBULANCE":
                caps.extend(["medical", "trauma_support", "patient_transport"])
            elif utype == "FIRE_TRUCK":
                caps.extend(["fire_suppression", "rescue", "hazmat"])
            elif utype == "HAZMAT":
                caps.extend(["chemical_containment", "decontamination", "hazmat"])
            elif utype == "RESCUE_BOAT":
                caps.extend(["water_rescue", "flood_evacuation", "search_rescue"])
            elif utype == "HELICOPTER":
                caps.extend(["aerial_recon", "air_evacuation", "medical"])

            units.append({
                "unit_code": code,
                "unit_type": utype,
                "name": name,
                "latitude": lat,
                "longitude": lng,
                "status": "AVAILABLE",
                "crew_size": rng.randint(2, 6),
                "capabilities": caps,
            })

        # 3. Generate Timeline Event Queue
        timeline = [
            {
                "simulated_time": 0,
                "event_type": "DISASTER_START",
                "title": f"Exercise Initiated: {template['name']}",
                "description": f"Simulation clock started. Scenario: {scenario_type}, Scale: {scale}, Seed: {seed}.",
                "data": {"scenario_type": scenario_type, "scale": scale, "seed": seed},
            },
            {
                "simulated_time": 5,
                "event_type": "NEW_INCIDENT",
                "title": "Initial Critical Incidents Reported",
                "description": f"{min(2, num_incidents)} critical emergency incidents registered in dispatch queue.",
                "data": {"incident_index_start": 0, "incident_count": min(2, num_incidents)},
            },
            {
                "simulated_time": 15,
                "event_type": "EVALUATE_INTELLIGENCE",
                "title": "Stage 8A AI Incident Intelligence Analysis",
                "description": "AI priority scoring engine analyzing urgency, hazard profile, and resource recommendations.",
                "data": {},
            },
            {
                "simulated_time": 25,
                "event_type": "OPTIMIZE_RESOURCES",
                "title": "Stage 8B Multi-Unit Fleet Resource Optimization",
                "description": "6-factor optimization engine assigning optimal simulation units.",
                "data": {},
            },
            {
                "simulated_time": 35,
                "event_type": "CREATE_DISPATCH",
                "title": "Stage 7B Automatic Mission Dispatch",
                "description": "Units dispatched and optimal emergency routes computed.",
                "data": {},
            },
            {
                "simulated_time": 60,
                "event_type": "TELEMETRY_STEP",
                "title": "Stage 7C Live Telemetry & Movement Tracking",
                "description": "Units navigating along active routes towards incident destinations.",
                "data": {},
            },
            {
                "simulated_time": 90,
                "event_type": "ROUTE_DEGRADATION_INJECT",
                "title": "Stage 8C Simulated Route Degradation Injected",
                "description": "Simulated hazard (low confidence / road obstruction) injected into active mission route.",
                "data": {"degradation_type": "LOW_CONFIDENCE"},
            },
            {
                "simulated_time": 95,
                "event_type": "ROUTE_HEALTH_CHECK",
                "title": "Stage 8C Route Health Monitor Evaluation",
                "description": "100-point route health scoring engine detected route degradation.",
                "data": {},
            },
            {
                "simulated_time": 105,
                "event_type": "REROUTE_RECOMMENDATION",
                "title": "Stage 8C AI Dynamic Re-Route Recommendation",
                "description": "Candidate alternative route generated providing higher health score.",
                "data": {},
            },
            {
                "simulated_time": 115,
                "event_type": "OPERATOR_REROUTE_APPROVE",
                "title": "Operator Reroute Approval Simulated",
                "description": "Dispatch operator confirms alternative AI route.",
                "data": {},
            },
            {
                "simulated_time": 180,
                "event_type": "MISSION_COMPLETE",
                "title": "Exercise Missions Completed & Incidents Resolved",
                "description": "Units arrived on scene and emergency operations completed successfully.",
                "data": {},
            },
        ]

        return {
            "scenario_type": scenario_type,
            "name": template["name"],
            "description": template["description"],
            "scale": scale,
            "seed": seed,
            "bounds": bounds,
            "incidents": incidents,
            "units": units,
            "timeline": timeline,
        }


scenario_generator = ScenarioGenerator()
