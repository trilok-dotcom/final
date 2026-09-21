import type {
  RouteHealth,
  AlternativeRoute,
  RerouteRecommendation,
  ApproveRerouteResponse,
} from '../types/rerouting';

const BASE_URL = '/api';

export async function evaluateRouteHealth(
  dispatchId: string,
  simulatedScenario?: string
): Promise<RouteHealth> {
  const response = await fetch(`${BASE_URL}/dispatches/${dispatchId}/evaluate-route`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ simulated_scenario: simulatedScenario || null }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Failed to evaluate route health' }));
    throw new Error(err.detail || 'Failed to evaluate route health');
  }

  return response.json();
}

export async function generateAlternatives(
  dispatchId: string
): Promise<{ success: boolean; alternatives: AlternativeRoute[] }> {
  const response = await fetch(`${BASE_URL}/dispatches/${dispatchId}/alternatives`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Failed to generate route alternatives' }));
    throw new Error(err.detail || 'Failed to generate route alternatives');
  }

  return response.json();
}

export async function evaluateReroute(
  dispatchId: string,
  simulatedScenario?: string
): Promise<RerouteRecommendation> {
  const response = await fetch(`${BASE_URL}/dispatches/${dispatchId}/reroute-evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ simulated_scenario: simulatedScenario || null }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Failed to evaluate reroute recommendation' }));
    throw new Error(err.detail || 'Failed to evaluate reroute recommendation');
  }

  return response.json();
}

export async function approveReroute(
  dispatchId: string,
  recommendedRouteId?: string,
  approvedBy: string = 'DISPATCH_OPERATOR'
): Promise<ApproveRerouteResponse> {
  const response = await fetch(`${BASE_URL}/dispatches/${dispatchId}/reroute-approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      recommended_route_id: recommendedRouteId || null,
      approved_by: approvedBy,
    }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Failed to approve reroute' }));
    throw new Error(err.detail || 'Failed to approve reroute');
  }

  return response.json();
}

export async function simulateRouteDegradation(
  dispatchId: string,
  scenario: string
): Promise<RerouteRecommendation> {
  const response = await fetch(`${BASE_URL}/dispatches/${dispatchId}/simulate-route-degradation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Failed to simulate route degradation' }));
    throw new Error(err.detail || 'Failed to simulate route degradation');
  }

  return response.json();
}
