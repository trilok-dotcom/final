export interface LocationPoint {
  lat: number;
  lng: number;
  address?: string;
  name?: string;
  elevationMeters?: number;
}

// Alias for LocationPoint to satisfy generic GIS terminology
export type RoutePoint = LocationPoint;

export type RiskLevel = 'low' | 'moderate' | 'high' | 'critical';

export interface RoadCondition {
  id: string;
  name: string;
  status: 'passable' | 'blocked' | 'flooded' | 'damaged';
  hazardType?: string;
  description?: string;
  impassableMeters?: number;
}

// Alias for RoadCondition
export type RoadSegment = RoadCondition;

export interface HazardInfo {
  id: string;
  title: string;
  severity: RiskLevel;
  location: LocationPoint;
  type: string;
  description: string;
}

export interface RouteStep {
  id: string;
  instruction: string;
  distanceMeters: number;
  durationSeconds: number;
  roadName: string;
  turnType: 'straight' | 'left' | 'right' | 'u_turn' | 'arrive' | 'start' | 'slight_left' | 'slight_right';
  riskLevel: RiskLevel;
  roadCondition?: RoadCondition;
  location?: [number, number]; // [lng, lat]
}

// Alias for RouteStep
export type Direction = RouteStep;

export interface RouteGeometry {
  type: 'LineString';
  coordinates: [number, number][]; // [longitude, latitude]
}

export interface RouteRequest {
  startLocation: LocationPoint;
  destination: LocationPoint;
  incidentId?: string;
  avoidFloodedRoads?: boolean;
  vehicleType?: string;
  maxRiskLevel?: RiskLevel;
}

export interface AlternativeRoute {
  id: string;
  title: string;
  distanceMeters: number;
  durationSeconds: number;
  riskLevel: RiskLevel;
  geometry: RouteGeometry;
}

export interface RouteResponse {
  id: string;
  totalDistanceMeters: number;
  estimatedDurationSeconds: number;
  status: 'calculated' | 'failed' | 'no_path_found' | 'off_road' | 'out_of_bounds';
  riskLevel: RiskLevel;
  steps: RouteStep[];
  geometry: RouteGeometry;
  roadConditions: RoadCondition[];
  hazards?: HazardInfo[];
  alternativeRoutes?: AlternativeRoute[];
  calculatedAt: string;
}

// Alias for RouteResponse
export type Route = RouteResponse;

// ==========================================
// RESQROUTE AI EMERGENCY ROUTING TYPES
// ==========================================

export interface SnappedLocation {
  lat: number;
  lng: number;
  distance_to_road_meters: number;
}

export interface AIRouteRequest {
  start: LocationPoint;
  destination: LocationPoint;
  vehicle_type?: string;
  avoid_low_confidence?: boolean;
}

export interface AIRouteStep {
  id: string;
  instruction: string;
  distance_meters: number;
  duration_seconds: number;
  road_name: string;
  turn_type: string;
  location: [number, number]; // [lng, lat]
}

export type RouteStepDetail = AIRouteStep;


export interface AIRouteResponse {
  success: boolean;
  route_id: string;
  status: 'calculated' | 'off_road' | 'no_path_found' | 'out_of_bounds';
  routing_engine: string;
  total_distance_meters: number;
  estimated_duration_seconds: number;
  average_confidence: number;
  risk_level: RiskLevel;
  snapped_start: SnappedLocation;
  snapped_destination: SnappedLocation;
  geometry: RouteGeometry;
  steps: AIRouteStep[];
}
