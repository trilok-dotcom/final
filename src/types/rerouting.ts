export type RouteHealthStatus = 'HEALTHY' | 'DEGRADED' | 'CRITICAL';

export type RerouteDecision =
  | 'NO_CHANGE'
  | 'MONITOR'
  | 'REROUTE_RECOMMENDED'
  | 'REROUTE_REQUIRED'
  | 'NO_ALTERNATIVE';

export interface CurrentRouteMetrics {
  route_id: string;
  distance_meters: number;
  eta_seconds: number;
  confidence: number;
  risk_level: string;
  health_score: number;
}

export interface RouteHealth {
  success: boolean;
  dispatch_id: string;
  route_health: RouteHealthStatus;
  health_score: number;
  overall_score: number;
  confidence_score: number;
  risk_score: number;
  eta_score: number;
  connectivity_score: number;
  deviation_score: number;
  degradation_detected: boolean;
  current_route: CurrentRouteMetrics;
  unit_deviation_meters: number;
  reasons: string[];
  reason_codes: string[];
  is_simulated?: boolean;
  evaluated_at: string;
}

export interface AlternativeRoute {
  route_id: string;
  dispatch_id: string;
  route_name: string;
  distance_meters: number;
  eta_seconds: number;
  confidence: number;
  risk_level: string;
  health_score: number;
  eta_improvement_seconds: number;
  confidence_improvement: number;
  risk_change: string;
  distance_difference_meters: number;
  health_improvement: number;
  route_geometry?: any;
  route_steps?: any[];
  generated_at: string;
}

export interface RerouteRecommendation {
  success: boolean;
  dispatch_id: string;
  decision: RerouteDecision;
  route_health: RouteHealthStatus;
  health_score: number;
  current_route_id: string;
  recommended_route_id: string | null;
  recommended_route: AlternativeRoute | null;
  health_improvement: number;
  eta_improvement_seconds: number;
  confidence_improvement: number;
  risk_change: string;
  reason_codes: string[];
  reasons: string[];
  explanation: string;
  alternatives: AlternativeRoute[];
  evaluated_at: string;
}

export interface ApproveRerouteResponse {
  success: boolean;
  status: string;
  dispatch_id: string;
  previous_route_id: string;
  new_route_id: string;
  distance_meters?: number;
  eta_seconds?: number;
  confidence?: number;
  risk_level?: string;
  approved_at?: string;
}

export interface RerouteEvent {
  id: string;
  dispatch_id: string;
  previous_route_id: string;
  new_route_id: string;
  trigger: string;
  reason: string;
  old_distance_meters: number;
  new_distance_meters: number;
  old_eta_seconds: number;
  new_eta_seconds: number;
  old_confidence: number;
  new_confidence: number;
  old_risk_level: string;
  new_risk_level: string;
  approved_by: string;
  approved_at: string;
  created_at: string;
}
