import { API_BASE_URL } from './api';
import type { LiveMission, MissionWebSocketMessage } from '../types/mission';

let socket: WebSocket | null = null;
let pollingInterval: any = null;
const listeners: Set<(msg: MissionWebSocketMessage) => void> = new Set();

function getWebSocketUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  // Use backend host or current host
  const host = API_BASE_URL.replace(/^https?:\/\//, '').replace(/\/api\/?$/, '');
  return `${protocol}//${host}/api/ws/missions`;
}

export function connectMissionWebSocket(
  onMessage: (msg: MissionWebSocketMessage) => void
): () => void {
  listeners.add(onMessage);

  if (!socket || socket.readyState === WebSocket.CLOSED) {
    try {
      const wsUrl = getWebSocketUrl();
      socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        console.log('Connected to RESQROUTE Live Mission Telemetry WebSocket');
        stopRestPollingFallback();
      };

      socket.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as MissionWebSocketMessage;
          listeners.forEach((listener) => listener(parsed));
        } catch {
          // Ignore malformed payloads
        }
      };

      socket.onerror = () => {
        console.warn('WebSocket telemetry stream error. Initiating REST polling fallback...');
        startRestPollingFallback();
      };

      socket.onclose = () => {
        console.warn('WebSocket connection closed. Reconnecting with REST polling fallback...');
        startRestPollingFallback();
      };
    } catch (err) {
      console.warn('Failed to initialize WebSocket:', err);
      startRestPollingFallback();
    }
  }

  return () => {
    listeners.delete(onMessage);
    if (listeners.size === 0 && socket) {
      socket.close();
      socket = null;
      stopRestPollingFallback();
    }
  };
}

function startRestPollingFallback() {
  if (pollingInterval) return;
  pollingInterval = setInterval(async () => {
    // Attempt WebSocket reconnect if closed
    if (!socket || socket.readyState === WebSocket.CLOSED) {
      try {
        const wsUrl = getWebSocketUrl();
        socket = new WebSocket(wsUrl);
      } catch {
        // Continue polling
      }
    }
  }, 5000);
}

function stopRestPollingFallback() {
  if (pollingInterval) {
    clearInterval(pollingInterval);
    pollingInterval = null;
  }
}

export async function getLiveMission(dispatchId: string): Promise<LiveMission> {
  const res = await fetch(`${API_BASE_URL}/dispatches/${dispatchId}/live`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch live mission telemetry for ${dispatchId}`);
  }
  return (await res.json()) as LiveMission;
}

export async function updateUnitLocation(
  dispatchId: string,
  lat: number,
  lng: number,
  speedKmh: number = 0.0,
  headingDegrees: number = 0.0
): Promise<LiveMission> {
  const res = await fetch(`${API_BASE_URL}/dispatches/${dispatchId}/location`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      lat,
      lng,
      speed_kmh: speedKmh,
      heading_degrees: headingDegrees,
    }),
  });
  if (!res.ok) {
    throw new Error('Failed to update live unit location');
  }
  return (await res.json()) as LiveMission;
}

export async function startMissionSimulation(dispatchId: string): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE_URL}/dispatches/${dispatchId}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to start mission movement simulation.');
  }
  return data;
}

export async function stopMissionSimulation(dispatchId: string): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE_URL}/dispatches/${dispatchId}/simulation/stop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to stop mission movement simulation.');
  }
  return data;
}
