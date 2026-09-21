import type { Incident } from './incident';
import type { RescueUnit } from './rescue';

export type ScenarioType =
  | 'URBAN_EARTHQUAKE'
  | 'URBAN_FLOOD'
  | 'INDUSTRIAL_FIRE'
  | 'MULTI_VEHICLE_ACCIDENT'
  | 'CUSTOM';

export type SimulationScale = 'SMALL' | 'MEDIUM' | 'LARGE';

export type SimulationStatus =
  | 'CREATED'
  | 'RUNNING'
  | 'PAUSED'
  | 'COMPLETED'
  | 'STOPPED'
  | 'FAILED';

export interface SimulationBounds {
  north: number;
  south: number;
  west: number;
  east: number;
}

export interface SimulationEvent {
  id: string;
  simulation_session_id: string;
  simulated_time: number;
  event_type: string;
  title: string;
  description?: string;
  data_json?: string;
  data?: any;
  status: 'PENDING' | 'EXECUTED' | 'SKIPPED';
  executed_at?: string | null;
  created_at: string;
}

export interface SimulationSession {
  id: string;
  scenario_type: ScenarioType | string;
  scenario_name: string;
  seed: number;
  scale: SimulationScale | string;
  status: SimulationStatus | string;
  simulation_time: number;
  speed: number;
  started_at?: string | null;
  paused_at?: string | null;
  completed_at?: string | null;
  stopped_at?: string | null;
  bounds_json?: string;
  bounds?: SimulationBounds;
  summary_json?: string;
  summary?: any;
  events?: SimulationEvent[];
  created_at: string;
  updated_at: string;
}

export interface CreateSimulationRequest {
  scenario_type: ScenarioType | string;
  scale: SimulationScale | string;
  seed: number;
  speed?: number;
  bounds?: SimulationBounds;
}

export interface TriggerEventRequest {
  event_type: string;
  dispatch_id?: string;
  incident_id?: string;
  data?: any;
}

export interface SimulationSummaryMetrics {
  incidents: number;
  critical_incidents: number;
  open_incidents: number;
  active_missions: number;
  completed_missions: number;
  available_units: number;
  dispatched_units: number;
  degraded_routes: number;
  reroute_recommendations: number;
}

export interface SimulationOverview {
  success: boolean;
  simulation: {
    id: string;
    scenario_type: string;
    scenario_name: string;
    seed: number;
    scale: string;
    status: string;
    simulation_time: number;
    speed: number;
    started_at?: string | null;
    completed_at?: string | null;
  };
  summary: SimulationSummaryMetrics;
  events: SimulationEvent[];
  incidents: Incident[];
  missions: any[];
  alerts: any[];
  map_layers: {
    incidents: Incident[];
    units: RescueUnit[];
    active_routes: any[];
  };
}
