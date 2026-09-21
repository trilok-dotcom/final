import type { RouteGeometry, RouteStep, RiskLevel } from './route';

export type DispatchStatus =
  | 'PENDING'
  | 'DISPATCHED'
  | 'EN_ROUTE'
  | 'ON_SCENE'
  | 'COMPLETED'
  | 'CANCELLED';

export interface DispatchRoute {
  route_id: string;
  distance_meters: number;
  estimated_duration_seconds: number;
  average_confidence: number;
  risk_level: RiskLevel | string;
  geometry: RouteGeometry;
  steps: RouteStep[] | any[];
}

export interface Dispatch {
  id: string;
  incident_id: string;
  rescue_unit_id: string;
  status: DispatchStatus | string;
  assigned_at: string;
  dispatched_at?: string | null;
  en_route_at?: string | null;
  arrived_at?: string | null;
  completed_at?: string | null;
  cancelled_at?: string | null;
  route_id?: string | null;
  distance_meters: number;
  estimated_duration_seconds: number;
  average_confidence: number;
  risk_level: string;
  route_geometry?: RouteGeometry | null;
  route_steps?: any[] | null;
  created_at: string;
  updated_at: string;
}

export interface DispatchResponse {
  success: boolean;
  dispatch_id: string;
  incident_id: string;
  incident_code?: string;
  rescue_unit_id: string;
  rescue_unit_code: string;
  rescue_unit_name?: string;
  vehicle_type?: string;
  status: DispatchStatus | string;
  route?: DispatchRoute | null;
  assigned_at: string;
  dispatched_at?: string | null;
  en_route_at?: string | null;
  arrived_at?: string | null;
  completed_at?: string | null;
  cancelled_at?: string | null;
}
