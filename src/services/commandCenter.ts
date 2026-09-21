import type { CommandCenterOverview } from '../types/commandCenter';

const BASE_URL = '/api';

export async function getCommandCenterOverview(): Promise<CommandCenterOverview> {
  const response = await fetch(`${BASE_URL}/command-center/overview`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Failed to fetch Command Center overview' }));
    throw new Error(err.detail || 'Failed to fetch Command Center overview');
  }

  return response.json();
}

export async function acknowledgeAlert(
  alertId: string,
  operatorId: string = 'DISPATCH_OPERATOR'
): Promise<{ success: boolean; message: string; alert: any }> {
  const response = await fetch(`${BASE_URL}/command-center/alerts/${alertId}/acknowledge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ operator_id: operatorId }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Failed to acknowledge alert' }));
    throw new Error(err.detail || 'Failed to acknowledge alert');
  }

  return response.json();
}
