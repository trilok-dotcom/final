import { API_BASE_URL } from './api';
import type { RescueUnit } from '../types/rescue';

export async function getRescueUnits(params?: {
  status?: string;
  unit_type?: string;
}): Promise<RescueUnit[]> {
  const url = new URL(`${API_BASE_URL}/rescue-units`);
  if (params?.status) url.searchParams.append('status', params.status);
  if (params?.unit_type) url.searchParams.append('unit_type', params.unit_type);

  try {
    const res = await fetch(url.toString(), {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data as RescueUnit[];
  } catch (error) {
    console.warn('Failed to fetch rescue units from backend, using fallback:', error);
    return [];
  }
}

export async function getRescueUnit(id: string): Promise<RescueUnit | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/rescue-units/${id}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) return null;
    return (await res.json()) as RescueUnit;
  } catch {
    return null;
  }
}

export async function createRescueUnit(payload: {
  unit_code: string;
  unit_type: string;
  status?: string;
  latitude: number;
  longitude: number;
  name: string;
  crew_size: number;
  capabilities: string[];
}): Promise<RescueUnit> {
  const res = await fetch(`${API_BASE_URL}/rescue-units`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to create rescue unit.');
  }

  return data as RescueUnit;
}

export async function updateRescueUnit(
  id: string,
  payload: Partial<RescueUnit>
): Promise<RescueUnit> {
  const res = await fetch(`${API_BASE_URL}/rescue-units/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to update rescue unit.');
  }

  return data as RescueUnit;
}

export async function updateRescueUnitStatus(
  id: string,
  status: string
): Promise<RescueUnit> {
  const res = await fetch(`${API_BASE_URL}/rescue-units/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to update rescue unit status.');
  }

  return data as RescueUnit;
}
