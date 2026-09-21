import { API_BASE_URL } from './api';
import type { ResourceOptimizationResponse, OptimizedDispatchResponse } from '../types/resourceOptimization';

export async function optimizeIncidentResources(incidentId: string): Promise<ResourceOptimizationResponse> {
  const res = await fetch(`${API_BASE_URL}/incidents/${incidentId}/optimize-resources`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to calculate resource optimization.');
  }

  return data as ResourceOptimizationResponse;
}

export async function dispatchOptimizedPlan(incidentId: string): Promise<OptimizedDispatchResponse> {
  const res = await fetch(`${API_BASE_URL}/incidents/${incidentId}/dispatch-optimized`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to dispatch optimized plan.');
  }

  return data as OptimizedDispatchResponse;
}
