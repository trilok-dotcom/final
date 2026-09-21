import type { LocationPoint } from './route';

export type RescueUnitType =
  | 'AMBULANCE'
  | 'FIRE_TRUCK'
  | 'POLICE'
  | 'RESCUE_TEAM'
  | 'DISASTER_RESPONSE'
  | 'helicopter'
  | 'medical_team'
  | 'heavy_rescue'
  | 'atv'
  | 'watercraft';

export type RescueUnitStatus =
  | 'AVAILABLE'
  | 'RESERVED'
  | 'DISPATCHED'
  | 'EN_ROUTE'
  | 'ON_SCENE'
  | 'RETURNING'
  | 'OFFLINE'
  | 'available'
  | 'reserved'
  | 'en_route'
  | 'on_scene'
  | 'offline';

export interface RescueUnit {
  id: string;
  unit_code: string;
  unit_type: RescueUnitType | string;
  status: RescueUnitStatus | string;
  latitude: number;
  longitude: number;
  name: string;
  crew_size: number;
  capabilities: string[];
  current_incident_id?: string | null;
  speed_kmh?: number;
  heading_degrees?: number;
  last_updated?: string;
  created_at?: string;
  updated_at?: string;

  // Legacy component properties for full backward compatibility
  unitCode?: string;
  type?: string;
  location?: LocationPoint;
  assignedIncidentId?: string;
  assignedIncidentCode?: string;
  crewCount?: number;
  equipmentSummary?: string;
  lastPing?: string;
  contactCallsign?: string;
}
