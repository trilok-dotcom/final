import React, { useState, useEffect, useCallback } from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { MapView } from '../components/map/MapView';
import { ScenarioSelector } from '../components/simulation/ScenarioSelector';
import { SimulationControls } from '../components/simulation/SimulationControls';
import { SimulationTimeline } from '../components/simulation/SimulationTimeline';
import { SimulationSummary } from '../components/simulation/SimulationSummary';
import { SimulationEventFeed } from '../components/simulation/SimulationEventFeed';
import { SimulationMissionPanel } from '../components/simulation/SimulationMissionPanel';

import {
  createSimulation,
  getSimulationOverview,
  startSimulation,
  pauseSimulation,
  resumeSimulation,
  stopSimulation,
  stepSimulation,
  setSimulationSpeed,
  triggerSimulationEvent,
  resetSimulation,
} from '../services/simulation';
import type {
  SimulationSession,
  SimulationOverview,
  CreateSimulationRequest,
} from '../types/simulation';

import { Cpu, Layers, X } from 'lucide-react';

export const SimulationCenterPage: React.FC = () => {
  const [activeSession, setActiveSession] = useState<SimulationSession | null>(null);
  const [overview, setOverview] = useState<SimulationOverview | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = useCallback(async (sessionId: string) => {
    try {
      const ov = await getSimulationOverview(sessionId);
      setOverview(ov);

      // Keep activeSession updated from overview
      if (ov.simulation) {
        setActiveSession((prev) => ({
          ...(prev || ({} as any)),
          ...ov.simulation,
          events: ov.events,
        }));
      }
    } catch (err: any) {
      console.error('Failed to fetch simulation overview:', err);
    }
  }, []);

  // Poll overview every 3 seconds if active session exists
  useEffect(() => {
    if (!activeSession) return;
    fetchOverview(activeSession.id);
    const interval = setInterval(() => {
      fetchOverview(activeSession.id);
    }, 3000);
    return () => clearInterval(interval);
  }, [activeSession?.id, fetchOverview]);

  // Handle Scenario Creation
  const handleCreateScenario = async (req: CreateSimulationRequest) => {
    setLoading(true);
    setError(null);
    try {
      const sess = await createSimulation(req);
      setActiveSession(sess);
      await fetchOverview(sess.id);
    } catch (err: any) {
      console.error('Failed to create simulation exercise:', err);
      setError(err.message || 'Failed to create simulation exercise');
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    if (!activeSession) return;
    setLoading(true);
    try {
      const updated = await startSimulation(activeSession.id);
      setActiveSession(updated);
      fetchOverview(activeSession.id);
    } catch (err: any) {
      setError(err.message || 'Failed to start simulation');
    } finally {
      setLoading(false);
    }
  };

  const handlePause = async () => {
    if (!activeSession) return;
    setLoading(true);
    try {
      const updated = await pauseSimulation(activeSession.id);
      setActiveSession(updated);
      fetchOverview(activeSession.id);
    } catch (err: any) {
      setError(err.message || 'Failed to pause simulation');
    } finally {
      setLoading(false);
    }
  };

  const handleResume = async () => {
    if (!activeSession) return;
    setLoading(true);
    try {
      const updated = await resumeSimulation(activeSession.id);
      setActiveSession(updated);
      fetchOverview(activeSession.id);
    } catch (err: any) {
      setError(err.message || 'Failed to resume simulation');
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    if (!activeSession) return;
    setLoading(true);
    try {
      const updated = await stopSimulation(activeSession.id);
      setActiveSession(updated);
      fetchOverview(activeSession.id);
    } catch (err: any) {
      setError(err.message || 'Failed to stop simulation');
    } finally {
      setLoading(false);
    }
  };

  const handleStep = async () => {
    if (!activeSession) return;
    try {
      const updated = await stepSimulation(activeSession.id, 5);
      setActiveSession(updated);
      fetchOverview(activeSession.id);
    } catch (err: any) {
      setError(err.message || 'Failed to step simulation');
    }
  };

  const handleSetSpeed = async (speed: number) => {
    if (!activeSession) return;
    try {
      const updated = await setSimulationSpeed(activeSession.id, speed);
      setActiveSession(updated);
    } catch (err: any) {
      setError(err.message || 'Failed to set speed');
    }
  };

  const handleTriggerEvent = async (event_type: string) => {
    if (!activeSession) return;
    try {
      await triggerSimulationEvent(activeSession.id, { event_type });
      fetchOverview(activeSession.id);
    } catch (err: any) {
      setError(err.message || 'Failed to trigger event');
    }
  };

  const handleReset = async () => {
    if (!activeSession) return;
    if (!window.confirm('Are you sure you want to reset and delete this simulation exercise session?')) return;
    setLoading(true);
    try {
      await resetSimulation(activeSession.id);
      setActiveSession(null);
      setOverview(null);
    } catch (err: any) {
      setError(err.message || 'Failed to reset simulation');
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageContainer>
      <div className="p-6 overflow-y-auto max-h-full space-y-6">
        {/* Header Bar with SIMULATION MODE Badge */}
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800/80 gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                <Cpu className="w-5 h-5 text-amber-500 animate-pulse" />
                RESQROUTE AI — Disaster Simulation Center
              </h1>
              <span className="px-2.5 py-1 rounded-lg bg-amber-500/20 border border-amber-500/40 text-amber-400 font-mono text-xs font-bold uppercase animate-pulse">
                ● SIMULATION MODE
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Stage 9B Simulation Orchestration Layer — End-to-End Multi-Incident Disaster Exercise Control Room
            </p>
          </div>

          <div className="flex items-center gap-3">
            {activeSession && (
              <button
                onClick={() => setActiveSession(null)}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-xs font-semibold transition"
              >
                + Create New Exercise
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="p-4 bg-rose-950/40 border border-rose-500/50 rounded-xl text-rose-300 text-xs flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-rose-400 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* If no active simulation, show ScenarioSelector */}
        {!activeSession ? (
          <div className="max-w-3xl mx-auto py-6">
            <ScenarioSelector onCreate={handleCreateScenario} loading={loading} />
          </div>
        ) : (
          <>
            {/* Playback Controls Bar */}
            <SimulationControls
              session={activeSession}
              onStart={handleStart}
              onPause={handlePause}
              onResume={handleResume}
              onStop={handleStop}
              onStep={handleStep}
              onSetSpeed={handleSetSpeed}
              onReset={handleReset}
              loading={loading}
            />

            {/* Timeline Progress */}
            {overview && (
              <SimulationTimeline
                events={overview.events || []}
                currentTime={activeSession.simulation_time}
              />
            )}

            {/* Summary Metrics */}
            {overview && (
              <SimulationSummary summary={overview.summary} session={activeSession} />
            )}

            {/* Main 2-Column Control Grid */}
            {overview && (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Left 7 Columns: Tactical Map View */}
                <div className="lg:col-span-7 bg-slate-900/80 backdrop-blur border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col min-h-[520px]">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
                    <div className="flex items-center gap-2">
                      <Layers className="w-5 h-5 text-amber-400" />
                      <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
                        Simulated Tactical Operations Map
                      </h2>
                    </div>
                    <span className="text-xs font-mono text-slate-400">
                      {overview.map_layers.incidents.length} Simulated Incidents •{' '}
                      {overview.map_layers.units.length} Units
                    </span>
                  </div>
                  <div className="flex-1 rounded-lg overflow-hidden border border-slate-800/80 relative">
                    <MapView
                      incidents={overview.map_layers.incidents}
                      rescueUnits={overview.map_layers.units}
                    />
                  </div>
                </div>

                {/* Right 5 Columns: Event Feed & Active Missions */}
                <div className="lg:col-span-5 flex flex-col gap-6">
                  <SimulationMissionPanel
                    missions={overview.missions || []}
                    onApproveReroute={async (dispatchId) => {
                      await triggerSimulationEvent(activeSession.id, {
                        event_type: 'OPERATOR_REROUTE_APPROVE',
                        dispatch_id: dispatchId,
                      });
                      fetchOverview(activeSession.id);
                    }}
                  />

                  <SimulationEventFeed
                    events={overview.events || []}
                    onTriggerEvent={handleTriggerEvent}
                  />
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </PageContainer>
  );
};
