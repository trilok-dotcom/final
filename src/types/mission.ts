export type MissionEventType =
  | 'MISSION_DISPATCHED'
  | 'MISSION_EN_ROUTE'
  | 'MISSION_ON_SCENE'
  | 'MISSION_COMPLETED'
  | 'MISSION_CANCELLED'
  | 'MISSION_UPDATE';

export interface MissionLocation {
  lat: number;
  lng: number;
}

export interface MissionTelemetry {
  id: string;
  dispatch_id: string;
  rescue_unit_id: string;
  incident_id: string;
  latitude: number;
  longitude: number;
  status: string;
  distance_remaining_meters: number;
  eta_seconds: number;
  progress_percent: number;
  speed_kmh: number;
  heading_degrees: number;
  timestamp: string;
}

export interface LiveMissionUnit {
  id: string;
  code: string;
  type: string;
  name?: string;
  lat: number;
  lng: number;
  speed_kmh: number;
  heading_degrees: number;
}

export interface LiveMissionIncident {
  id: string;
  code?: string;
  lat: number;
  lng: number;
  location_name?: string;
}

export interface LiveMission {
  dispatch_id: string;
  status: string;
  unit: LiveMissionUnit;
  incident: LiveMissionIncident;
  distance_remaining_meters: number;
  eta_seconds: number;
  progress_percent: number;
  risk_level: string;
  average_ai_confidence: number;
  route_geometry?: {
    type: 'LineString';
    coordinates: [number, number][];
  };
}

export interface MissionWebSocketMessage {
  type: MissionEventType | string;
  dispatch_id?: string;
  unit_id?: string;
  incident_id?: string;
  status?: string;
  location?: MissionLocation;
  speed_kmh?: number;
  heading_degrees?: number;
  distance_remaining_meters?: number;
  eta_seconds?: number;
  progress_percent?: number;
  timestamp?: string;
  message?: string;
}
