import { API_BASE_URL } from './api';
import type { Dispatch, DispatchResponse } from '../types/dispatch';

export async function dispatchIncident(incidentId: string): Promise<DispatchResponse> {
  const res = await fetch(`${API_BASE_URL}/dispatch/incident/${incidentId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  const data = await res.json();
  if (!res.ok) {
    if (data.detail && typeof data.detail === 'object' && data.detail.message) {
      throw new Error(data.detail.message);
    }
    throw new Error(data.detail || 'Failed to dispatch rescue unit for incident.');
  }

  return data as DispatchResponse;
}

export async function getDispatches(status?: string): Promise<Dispatch[]> {
  const url = new URL(`${API_BASE_URL}/dispatches`);
  if (status) url.searchParams.append('status', status);

  try {
    const res = await fetch(url.toString(), {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as Dispatch[];
  } catch (error) {
    console.warn('Failed to fetch dispatches from backend:', error);
    return [];
  }
}

export async function getDispatch(id: string): Promise<Dispatch | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/dispatches/${id}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) return null;
    return (await res.json()) as Dispatch;
  } catch {
    return null;
  }
}

export async function updateDispatchStatus(
  id: string,
  status: string
): Promise<Dispatch> {
  const res = await fetch(`${API_BASE_URL}/dispatches/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });

  const data = await res.json();
  if (!res.ok) {
    if (data.detail && typeof data.detail === 'object' && data.detail.message) {
      throw new Error(data.detail.message);
    }
    throw new Error(data.detail || 'Failed to update dispatch status.');
  }

  return data as Dispatch;
}
