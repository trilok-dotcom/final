import { API_BASE_URL } from './api';
import type { IncidentIntelligence } from '../types/intelligence';

export async function analyzeIncident(incidentId: string): Promise<IncidentIntelligence> {
  const res = await fetch(`${API_BASE_URL}/incidents/${incidentId}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to execute AI incident analysis.');
  }

  return data as IncidentIntelligence;
}

export async function getIncidentIntelligence(incidentId: string): Promise<IncidentIntelligence | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/incidents/${incidentId}/intelligence`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) return null;
    return (await res.json()) as IncidentIntelligence;
  } catch {
    return null;
  }
}
