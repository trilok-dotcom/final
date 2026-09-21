import type { Incident } from './incident';
import type { RescueUnit } from './rescue';

export interface CommandCenterSummary {
  total_incidents: number;
  open_incidents: number;
  critical_incidents: number;
  high_incidents: number;
  total_units: number;
  available_units: number;
  busy_units: number;
  active_missions: number;
  pending_dispatches: number;
  degraded_routes: number;
  unacknowledged_alerts: number;
}

export interface CommandPriorityIncident {
  incident: Incident;
  intelligence: any | null;
  intelligence_score: number;
  urgency_level: string;
  recommended_actions: string[];
  assigned_mission: any | null;
  has_active_mission: boolean;
}

export interface CommandActiveMission {
  dispatch_id: string;
  incident_id: string;
  unit_id: string;
  incident_title: string;
  incident_type: string;
  incident_severity: string;
  unit_name: string;
  unit_type: string;
  status: string;
  assigned_route_id: string;
  current_location: [number, number] | null;
  destination: [number, number];
  distance_remaining_km: number | null;
  eta_seconds: number | null;
  telemetry: any | null;
  route_health: any | null;
  health_status: string;
  route_confidence: number | null;
}

export interface ResourceGroupSummary {
  unit_type: string;
  total: number;
  available: number;
  dispatched: number;
  maintenance: number;
  units: RescueUnit[];
}

export interface CommandCenterAlert {
  id: string;
  alert_type: 'SEVERITY_CRITICAL' | 'ROUTE_DEGRADATION' | 'UNASSIGNED_CRITICAL' | 'MISSION_DELAY' | 'NO_UNIT_AVAILABLE' | 'SYSTEM_INFO';
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'INFO';
  title: string;
  message: string;
  incident_id: string | null;
  dispatch_id: string | null;
  unit_id: string | null;
  created_at: string;
  acknowledged: boolean;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
}

export interface CommandCenterOverview {
  summary: CommandCenterSummary;
  priority_queue: CommandPriorityIncident[];
  active_missions: CommandActiveMission[];
  resource_overview: ResourceGroupSummary[];
  alerts: CommandCenterAlert[];
  map_layers: {
    incidents: Incident[];
    units: RescueUnit[];
    active_routes: any[];
  };
  last_updated: string;
}
