import type { LocationPoint } from './route';

export type IncidentSeverity =
  | 'CRITICAL'
  | 'HIGH'
  | 'MEDIUM'
  | 'LOW'
  | 'critical'
  | 'high'
  | 'moderate'
  | 'low';

export type IncidentStatus =
  | 'REPORTED'
  | 'VERIFIED'
  | 'DISPATCHING'
  | 'ACTIVE'
  | 'RESOLVED'
  | 'CANCELLED'
  | 'unassigned'
  | 'in_progress'
  | 'dispatched'
  | 'resolved';

export type IncidentType =
  | 'FIRE'
  | 'MEDICAL'
  | 'ACCIDENT'
  | 'FLOOD'
  | 'COLLAPSED_BUILDING'
  | 'EARTHQUAKE'
  | 'MISSING_PERSON'
  | 'HAZMAT'
  | 'OTHER'
  | 'flood'
  | 'earthquake'
  | 'fire'
  | 'landslide'
  | 'building_collapse'
  | 'storm'
  | 'tsunami';

export interface EmergencyIncident {
  id: string;
  incident_code: string;
  incident_type: IncidentType | string;
  severity: IncidentSeverity | string;
  status: IncidentStatus | string;
  latitude: number;
  longitude: number;
  location_name?: string;
  description?: string;
  reported_by?: string;
  assigned_unit_id?: string | null;
  created_at?: string;
  updated_at?: string;
  resolved_at?: string | null;

  // Legacy component properties for full backward compatibility
  code?: string;
  title?: string;
  type?: string;
  location?: LocationPoint;
  reportedAt?: string;
  affectedRadiusKm?: number;
  assignedUnitsCount?: number;
}

export type Incident = EmergencyIncident;
