import { ApiClient, API_BASE_URL } from './api';
import type {
  RouteRequest,
  RouteResponse,
  RouteStep,
  RiskLevel,
  AIRouteRequest,
  AIRouteResponse,
} from '../types/route';

interface BackendRouteStep {
  id: string;
  instruction: string;
  distance_meters: number;
  duration_seconds: number;
  road_name: string;
  turn_type: 'straight' | 'left' | 'right' | 'u_turn' | 'arrive' | 'start';
  risk_level: RiskLevel;
  location?: [number, number];
}

interface BackendRouteResponse {
  id: string;
  total_distance_meters: number;
  estimated_duration_seconds: number;
  status: 'calculated' | 'failed' | 'no_path_found';
  risk_level: RiskLevel;
  steps: BackendRouteStep[];
  geometry: {
    type: 'LineString';
    coordinates: [number, number][]; // [longitude, latitude]
  };
  road_conditions: any[];
  calculated_at: string;
}

/**
 * RESQROUTE Routing Service (OSRM & AI Engine Connected)
 */

export async function calculateRescueRoute(request: RouteRequest): Promise<RouteResponse> {
  const payload = {
    start: {
      lat: request.startLocation.lat,
      lng: request.startLocation.lng,
      name: request.startLocation.name || 'Start Location',
      address: request.startLocation.address,
    },
    destination: {
      lat: request.destination.lat,
      lng: request.destination.lng,
      name: request.destination.name || 'Disaster Destination',
      address: request.destination.address,
    },
    incident_id: request.incidentId,
  };

  const raw = await ApiClient.post<BackendRouteResponse>('/route', payload);

  // Map backend response into frontend RouteResponse
  const steps: RouteStep[] = raw.steps.map((s) => ({
    id: s.id,
    instruction: s.instruction,
    distanceMeters: s.distance_meters,
    durationSeconds: s.duration_seconds,
    roadName: s.road_name,
    turnType: s.turn_type,
    riskLevel: s.risk_level || 'low',
  }));

  return {
    id: raw.id,
    totalDistanceMeters: raw.total_distance_meters,
    estimatedDurationSeconds: raw.estimated_duration_seconds,
    status: raw.status,
    riskLevel: raw.risk_level || 'low',
    steps,
    geometry: raw.geometry,
    roadConditions: raw.road_conditions || [],
    calculatedAt: raw.calculated_at,
  };
}

/**
 * Calculate AI Emergency Route using U-Net extracted road network graph.
 */
export async function calculateAIRoute(request: AIRouteRequest): Promise<AIRouteResponse> {
  const payload = {
    start: {
      lat: request.start.lat,
      lng: request.start.lng,
      name: request.start.name || 'Emergency Origin',
      address: request.start.address,
    },
    destination: {
      lat: request.destination.lat,
      lng: request.destination.lng,
      name: request.destination.name || 'Emergency Destination',
      address: request.destination.address,
    },
    vehicle_type: request.vehicle_type || 'ambulance',
    avoid_low_confidence: request.avoid_low_confidence ?? true,
  };

  // Endpoint: POST /api/ai/route (also mounted at /api/v1/ai/route)
  // Determine root API URL (strip trailing /api/v1 if needed or call direct endpoint)
  const rootUrl = API_BASE_URL.replace(/\/api\/v1\/?$/, '');
  const targetUrl = `${rootUrl}/api/ai/route`;

  try {
    const response = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      if (data && data.detail) {
        if (typeof data.detail === 'object' && data.detail.message) {
          throw new Error(data.detail.message);
        } else if (typeof data.detail === 'string') {
          throw new Error(data.detail);
        }
      }
      throw new Error(`AI Route calculation failed with status ${response.status}`);
    }

    if (!data || !data.success) {
      const msg = data.message || 'Failed to calculate AI emergency route.';
      throw new Error(msg);
    }

    return data as AIRouteResponse;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Unable to connect to the RESQROUTE AI routing service.');
  }
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await ApiClient.get<{ status: string }>('/health');
    return res.status === 'ok';
  } catch {
    return false;
  }
}
