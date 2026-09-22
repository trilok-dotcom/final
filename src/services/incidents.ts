import { API_BASE_URL } from './api';
import type { EmergencyIncident } from '../types/incident';

export async function getIncidents(params?: {
  status?: string;
  severity?: string;
  incident_type?: string;
}): Promise<EmergencyIncident[]> {
  const url = new URL(`${API_BASE_URL}/incidents`);
  if (params?.status) url.searchParams.append('status', params.status);
  if (params?.severity) url.searchParams.append('severity', params.severity);
  if (params?.incident_type) url.searchParams.append('incident_type', params.incident_type);

  try {
    const res = await fetch(url.toString(), {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data as EmergencyIncident[];
  } catch (error) {
    console.warn('Failed to fetch incidents from backend, using fallback:', error);
    return [];
  }
}

export async function getIncident(id: string): Promise<EmergencyIncident | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/incidents/${id}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) return null;
    return (await res.json()) as EmergencyIncident;
  } catch {
    return null;
  }
}

export async function createIncident(payload: {
  incident_type: string;
  severity: string;
  latitude: number;
  longitude: number;
  location_name?: string;
  description?: string;
  reported_by?: string;
  location_source?: string;
  location_accuracy?: number;
  timestamp?: string;
}): Promise<EmergencyIncident> {
  const res = await fetch(`${API_BASE_URL}/incidents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to create emergency incident.');
  }

  return data as EmergencyIncident;
}

export async function updateIncident(
  id: string,
  payload: Partial<EmergencyIncident>
): Promise<EmergencyIncident> {
  const res = await fetch(`${API_BASE_URL}/incidents/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to update emergency incident.');
  }

  return data as EmergencyIncident;
}

export async function resolveIncident(id: string): Promise<EmergencyIncident> {
  const res = await fetch(`${API_BASE_URL}/incidents/${id}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to resolve emergency incident.');
  }

  return data as EmergencyIncident;
}
