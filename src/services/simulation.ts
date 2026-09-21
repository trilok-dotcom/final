import type {
  SimulationSession,
  SimulationOverview,
  CreateSimulationRequest,
  TriggerEventRequest,
} from '../types/simulation';

const BASE_URL = '/api';

export const createSimulation = async (
  data: CreateSimulationRequest
): Promise<SimulationSession> => {
  const response = await fetch(`${BASE_URL}/simulations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Failed to create simulation' }));
    throw new Error(err.detail || 'Failed to create simulation');
  }
  const resData = await response.json();
  return resData.simulation;
};

export const listSimulations = async (): Promise<SimulationSession[]> => {
  const response = await fetch(`${BASE_URL}/simulations`);
  if (!response.ok) {
    throw new Error('Failed to list simulations');
  }
  return response.json();
};

export const getSimulation = async (
  simulationId: string
): Promise<SimulationSession> => {
  const response = await fetch(`${BASE_URL}/simulations/${simulationId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch simulation ${simulationId}`);
  }
  const resData = await response.json();
  return resData.simulation;
};

export const getSimulationOverview = async (
  simulationId: string
): Promise<SimulationOverview> => {
  const response = await fetch(`${BASE_URL}/simulations/${simulationId}/overview`);
  if (!response.ok) {
    throw new Error(`Failed to fetch simulation overview for ${simulationId}`);
  }
  return response.json();
};

export const startSimulation = async (
  simulationId: string
): Promise<SimulationSession> => {
  const response = await fetch(`${BASE_URL}/simulations/${simulationId}/start`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`Failed to start simulation ${simulationId}`);
  }
  const resData = await response.json();
  return resData.simulation;
};

export const pauseSimulation = async (
  simulationId: string
): Promise<SimulationSession> => {
  const response = await fetch(`${BASE_URL}/simulations/${simulationId}/pause`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`Failed to pause simulation ${simulationId}`);
  }
  const resData = await response.json();
  return resData.simulation;
};

export const resumeSimulation = async (
  simulationId: string
): Promise<SimulationSession> => {
  const response = await fetch(`${BASE_URL}/simulations/${simulationId}/resume`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`Failed to resume simulation ${simulationId}`);
  }
  const resData = await response.json();
  return resData.simulation;
};

export const stopSimulation = async (
  simulationId: string
): Promise<SimulationSession> => {
  const response = await fetch(`${BASE_URL}/simulations/${simulationId}/stop`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`Failed to stop simulation ${simulationId}`);
  }
  const resData = await response.json();
  return resData.simulation;
};

export const stepSimulation = async (
  simulationId: string,
  seconds: number = 5
): Promise<SimulationSession> => {
  const response = await fetch(`${BASE_URL}/simulations/${simulationId}/step`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ seconds }),
  });
  if (!response.ok) {
    throw new Error(`Failed to step simulation ${simulationId}`);
  }
  const resData = await response.json();
  return resData.simulation;
};

export const setSimulationSpeed = async (
  simulationId: string,
  speed: number
): Promise<SimulationSession> => {
  const response = await fetch(`${BASE_URL}/simulations/${simulationId}/speed`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ speed }),
  });
  if (!response.ok) {
    throw new Error(`Failed to set simulation speed for ${simulationId}`);
  }
  const resData = await response.json();
  return resData.simulation;
};

export const triggerSimulationEvent = async (
  simulationId: string,
  data: TriggerEventRequest
): Promise<SimulationSession> => {
  const response = await fetch(`${BASE_URL}/simulations/${simulationId}/trigger-event`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error(`Failed to trigger simulation event for ${simulationId}`);
  }
  const resData = await response.json();
  return resData.simulation;
};

export const resetSimulation = async (
  simulationId: string
): Promise<{ success: boolean; message: string }> => {
  const response = await fetch(`${BASE_URL}/simulations/${simulationId}/reset`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`Failed to reset simulation ${simulationId}`);
  }
  return response.json();
};
