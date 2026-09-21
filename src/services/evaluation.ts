import type { EvaluationOverview, EvaluationRun } from '../types/evaluation';

const API_BASE = '/api/evaluation';

export const evaluationService = {
  async getOverview(): Promise<EvaluationOverview> {
    const res = await fetch(`${API_BASE}/overview`);
    if (!res.ok) throw new Error('Failed to fetch evaluation overview');
    return res.json();
  },

  async getRuns(): Promise<EvaluationRun[]> {
    const res = await fetch(`${API_BASE}/runs`);
    if (!res.ok) throw new Error('Failed to fetch evaluation runs');
    const data = await res.json();
    return data.runs || [];
  },

  async getRun(runId: string): Promise<EvaluationRun> {
    const res = await fetch(`${API_BASE}/runs/${runId}`);
    if (!res.ok) throw new Error(`Failed to fetch evaluation run ${runId}`);
    const data = await res.json();
    return data.data;
  },

  async runAiEval(sampleCount: number = 50): Promise<any> {
    const res = await fetch(`${API_BASE}/ai`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sample_count: sampleCount }),
    });
    if (!res.ok) throw new Error('Failed to run AI evaluation');
    return res.json();
  },

  async runRoutingEval(sampleCount: number = 20): Promise<any> {
    const res = await fetch(`${API_BASE}/routing`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sample_count: sampleCount }),
    });
    if (!res.ok) throw new Error('Failed to run routing evaluation');
    return res.json();
  },

  async runReroutingEval(): Promise<any> {
    const res = await fetch(`${API_BASE}/rerouting`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to run rerouting evaluation');
    return res.json();
  },

  async runResourcesEval(): Promise<any> {
    const res = await fetch(`${API_BASE}/resources`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to run resources evaluation');
    return res.json();
  },

  async runMissionsEval(): Promise<any> {
    const res = await fetch(`${API_BASE}/missions`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to run missions evaluation');
    return res.json();
  },

  async runSimulationEval(simulationId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/simulation/${simulationId}`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to run simulation evaluation');
    return res.json();
  },

  async runOsrmBaseline(sampleCount: number = 10): Promise<any> {
    const res = await fetch(`${API_BASE}/baseline/osrm?sample_count=${sampleCount}`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to run OSRM baseline evaluation');
    return res.json();
  },

  async runNearestUnitBaseline(sampleCount: number = 10): Promise<any> {
    const res = await fetch(`${API_BASE}/baseline/nearest-unit?sample_count=${sampleCount}`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to run Nearest Unit baseline evaluation');
    return res.json();
  },

  getExportUrl(runId: string, format: 'json' | 'csv'): string {
    return `${API_BASE}/runs/${runId}/export?format=${format}`;
  },
};
