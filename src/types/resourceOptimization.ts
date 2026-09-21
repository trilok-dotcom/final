export type ResourceOptimizationStatus =
  | 'OPTIMAL'
  | 'PARTIAL'
  | 'INSUFFICIENT_RESOURCES'
  | 'NO_SUITABLE_UNITS'
  | 'CONFLICT'
  | 'ALREADY_DISPATCHED';

export interface ResourceRequirement {
  unit_type: string;
  required: number;
  available: number;
  selected: number;
}

export interface FactorBreakdown {
  eta_score: number;
  route_safety_score: number;
  ai_confidence_score: number;
  capability_score: number;
  availability_score: number;
  operational_score: number;
}

export interface CandidateUnit {
  rescue_unit_id: string;
  unit_code: string;
  unit_name: string;
  unit_type: string;
  status: string;
  optimization_score: number;
  distance_meters: number;
  estimated_duration_seconds: number;
  average_confidence: number;
  risk_level: string;
  is_selected: boolean;
  selection_reason: string;
  factor_breakdown: FactorBreakdown;
  route_geometry?: {
    type: 'LineString';
    coordinates: [number, number][];
  };
}

export interface SelectedUnit {
  rescue_unit_id: string;
  unit_code: string;
  unit_name: string;
  unit_type: string;
  optimization_score: number;
  distance_meters: number;
  estimated_duration_seconds: number;
  average_confidence: number;
  risk_level: string;
  selection_reason: string;
  factor_breakdown: FactorBreakdown;
  route_geometry?: {
    type: 'LineString';
    coordinates: [number, number][];
  };
}

export interface ResourceOptimizationResponse {
  success: boolean;
  incident_id: string;
  incident_code?: string;
  resource_status: ResourceOptimizationStatus | string;
  required_resources: ResourceRequirement[];
  selected_units: SelectedUnit[];
  candidate_units: CandidateUnit[];
  optimization_summary: string;
  analyzed_at: string;
}

export interface OptimizedDispatchResponse {
  success: boolean;
  incident_id: string;
  incident_code?: string;
  dispatched_units_count: number;
  dispatch_ids: string[];
  dispatches: any[];
  message: string;
}
