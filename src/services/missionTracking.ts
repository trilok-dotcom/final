import { API_BASE_URL, getBackendOrigin } from './api';
import type { LiveMission, MissionWebSocketMessage } from '../types/mission';

export interface LocationTelemetryPayload {
  lat: number;
  lng: number;
  accuracy?: number;
  speed_kmh?: number;
  heading_degrees?: number;
  timestamp?: string;
}

export interface LiveMissionResponseData {
  dispatch_id: string;
  status: string;
  unit: {
    id: string;
    code: string;
    type: string;
    name?: string;
    lat: number;
    lng: number;
    speed_kmh: number;
    heading_degrees: number;
    accuracy?: number;
  };
  incident: {
    id: string;
    code?: string;
    lat: number;
    lng: number;
    location_name?: string;
  };
  distance_remaining_meters: number;
  eta_seconds: number;
  progress_percent: number;
  risk_level: string;
  average_ai_confidence: number;
  route_health?: string;
  reroute_recommendation?: any;
  route_geometry?: any;
}

export async function sendLocationTelemetry(
  dispatchId: string,
  payload: LocationTelemetryPayload
): Promise<LiveMissionResponseData> {
  const res = await fetch(`${API_BASE_URL}/dispatches/${dispatchId}/location`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Failed to send telemetry update.');
  }

  return data as LiveMissionResponseData;
}

export async function getLiveMissionTelemetry(dispatchId: string): Promise<LiveMissionResponseData> {
  const res = await fetch(`${API_BASE_URL}/dispatches/${dispatchId}/live`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Failed to fetch live mission.');
  }

  return data as LiveMissionResponseData;
}

export async function getLiveMission(dispatchId: string): Promise<LiveMission> {
  const res = await fetch(`${API_BASE_URL}/dispatches/${dispatchId}/live`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Failed to fetch live mission details.');
  }

  return data as LiveMission;
}

export async function startMissionSimulation(dispatchId: string): Promise<{ success: boolean; message?: string }> {
  const res = await fetch(`${API_BASE_URL}/dispatches/${dispatchId}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Failed to start mission simulation.');
  }

  return data;
}

export async function stopMissionSimulation(dispatchId: string): Promise<{ success: boolean; message?: string }> {
  const res = await fetch(`${API_BASE_URL}/dispatches/${dispatchId}/simulation/stop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Failed to stop mission simulation.');
  }

  return data;
}

export function connectMissionWebSocket(
  onMessage: (msg: MissionWebSocketMessage) => void,
  onError?: (err: Event) => void
): () => void {
  let wsUrl: string;
  if (import.meta.env.VITE_WS_BASE_URL) {
    const rawWs = import.meta.env.VITE_WS_BASE_URL.replace(/\/+$/, '');
    wsUrl = rawWs.includes('/ws') ? rawWs : `${rawWs}/api/ws/missions`;
  } else {
    const origin = getBackendOrigin();
    const wsProto = origin.startsWith('https:') ? 'wss:' : 'ws:';
    const host = origin.replace(/^https?:\/\//, '');
    wsUrl = `${wsProto}//${host}/api/ws/missions`;
  }

  const socket = new WebSocket(wsUrl);

  socket.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data) as MissionWebSocketMessage;
      onMessage(parsed);
    } catch (e) {
      console.warn('Failed to parse WebSocket message:', e);
    }
  };

  if (onError) {
    socket.onerror = onError;
  }

  return () => {
    if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
      socket.close();
    }
  };
}
