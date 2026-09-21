import React, { useState, useEffect, useCallback } from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { MapView } from '../components/map/MapView';
import { CommandSummaryCards } from '../components/command/CommandSummaryCards';
import { IncidentPriorityQueue } from '../components/command/IncidentPriorityQueue';
import { ActiveMissionTable } from '../components/command/ActiveMissionTable';
import { ResourceOverview } from '../components/command/ResourceOverview';
import { CommandAlertFeed } from '../components/command/CommandAlertFeed';
import { ActiveMissionPanel } from '../components/dispatch/ActiveMissionPanel';
import { ResourceOptimizationPanel } from '../components/incidents/ResourceOptimizationPanel';

import { getCommandCenterOverview, acknowledgeAlert } from '../services/commandCenter';
import { dispatchIncident } from '../services/dispatch';
import { optimizeIncidentResources } from '../services/resourceOptimization';
import type { CommandCenterOverview } from '../types/commandCenter';
import type { ResourceOptimizationResponse } from '../types/resourceOptimization';
import type { DispatchResponse } from '../types/dispatch';

import {
  RefreshCw,
  Zap,
  Navigation,
  Shield,
  AlertOctagon,
  X,
  Loader2,
  Radio,
  Layers,
} from 'lucide-react';

export const CommandCenterPage: React.FC = () => {
  const [overview, setOverview] = useState<CommandCenterOverview | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'QUEUE' | 'MISSIONS' | 'RESOURCES' | 'ALERTS'>('QUEUE');

  // Selected state for modals & maps
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [activeDispatchResponse, setActiveDispatchResponse] = useState<DispatchResponse | null>(null);
  const [activeOptimization, setActiveOptimization] = useState<ResourceOptimizationResponse | null>(null);

  const fetchOverview = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) setRefreshing(true);
    try {
      const data = await getCommandCenterOverview();
      setOverview(data);
      setError(null);
    } catch (err: any) {
      console.error('Failed to load Command Center overview:', err);
      setError(err.message || 'Failed to load Command Center overview');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // Poll every 4 seconds for live command center state
  useEffect(() => {
    fetchOverview();
    const interval = setInterval(() => {
      fetchOverview();
    }, 4000);
    return () => clearInterval(interval);
  }, [fetchOverview]);

  // Handle alert acknowledgement
  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await acknowledgeAlert(alertId, 'DISPATCH_OPERATOR');
      fetchOverview();
    } catch (err: any) {
      console.error('Failed to acknowledge alert:', err);
    }
  };

  // Handle direct single unit dispatch
  const handleDispatchIncident = async (incidentId: string) => {
    try {
      const res = await dispatchIncident(incidentId);
      setActiveDispatchResponse(res);
      fetchOverview();
    } catch (err: any) {
      alert(`Dispatch failed: ${err.message || err}`);
    }
  };

  // Handle Stage 8B multi-unit resource optimization trigger
  const handleOptimizeIncident = async (incidentId: string) => {
    try {
      const opt = await optimizeIncidentResources(incidentId);
      setActiveOptimization(opt);
    } catch (err: any) {
      alert(`Resource optimization failed: ${err.message || err}`);
    }
  };

  // Handle card filter click
  const handleFilterClick = (filterType: string) => {
    switch (filterType) {
      case 'incidents':
        setActiveTab('QUEUE');
        break;
      case 'fleet':
        setActiveTab('RESOURCES');
        break;
      case 'missions':
        setActiveTab('MISSIONS');
        break;
      case 'alerts':
        setActiveTab('ALERTS');
        break;
      default:
        break;
    }
  };

  const openMissionPanel = (dispatchId: string) => {
    if (!overview) return;
    const found = overview.active_missions.find((m) => m.dispatch_id === dispatchId);
    if (found) {
      setActiveDispatchResponse({
        success: true,
        dispatch_id: found.dispatch_id,
        incident_id: found.incident_id,
        rescue_unit_id: found.unit_id,
        rescue_unit_code: found.unit_name,
        rescue_unit_name: found.unit_name,
        vehicle_type: found.unit_type,
        status: found.status,
        assigned_at: overview.last_updated,
      });
    }
  };

  if (loading && !overview) {
    return (
      <PageContainer>
        <div className="flex flex-col items-center justify-center py-24 text-slate-400">
          <Loader2 className="w-10 h-10 animate-spin text-amber-500 mb-4" />
          <p className="text-sm font-semibold uppercase tracking-wider">Loading Command Center Aggregation Engine...</p>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div className="p-6 overflow-y-auto max-h-full">
        {/* Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800/80 mb-6 gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              <Radio className="w-5 h-5 text-amber-500 animate-pulse" />
              Disaster Operations Command Center
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Stage 9A Operations Control Panel — Real-Time Incident Priority Queue, Fleet Telemetry & Dynamic Route Integrity
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold font-mono">
              <Radio className="w-4 h-4 animate-pulse" />
              LIVE TELEMETRY
            </div>
            <button
              onClick={() => fetchOverview(true)}
              disabled={refreshing}
              className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-rose-950/40 border border-rose-500/50 rounded-xl text-rose-300 text-xs flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-rose-400 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {overview && (
          <>
            {/* Top Aggregated Summary Cards */}
            <CommandSummaryCards summary={overview.summary} onFilterClick={handleFilterClick} />

            {/* Main 2-Column Command Control Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
              {/* Left 7 Columns: Interactive Command Map */}
              <div className="lg:col-span-7 bg-slate-900/80 backdrop-blur border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col min-h-[560px]">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
                  <div className="flex items-center gap-2">
                    <Layers className="w-5 h-5 text-amber-400" />
                    <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
                      Tactical Operations Map View
                    </h2>
                  </div>
                  <span className="text-xs font-mono text-slate-400">
                    {overview.map_layers.incidents.length} Incidents • {overview.map_layers.units.length} Units
                  </span>
                </div>
                <div className="flex-1 rounded-lg overflow-hidden border border-slate-800/80 relative">
                  <MapView
                    incidents={overview.map_layers.incidents}
                    rescueUnits={overview.map_layers.units}
                    onIncidentSelect={(id) => setSelectedIncidentId(id)}
                  />
                </div>
              </div>

              {/* Right 5 Columns: Operations Control Panel with Tabs */}
              <div className="lg:col-span-5 flex flex-col h-[560px]">
                {/* Tab Navigation */}
                <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 mb-3">
                  <button
                    onClick={() => setActiveTab('QUEUE')}
                    className={`flex-1 py-2 px-2 rounded-lg text-xs font-semibold transition flex items-center justify-center gap-1.5 ${
                      activeTab === 'QUEUE'
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Zap className="w-3.5 h-3.5" />
                    Priority Queue
                  </button>
                  <button
                    onClick={() => setActiveTab('MISSIONS')}
                    className={`flex-1 py-2 px-2 rounded-lg text-xs font-semibold transition flex items-center justify-center gap-1.5 ${
                      activeTab === 'MISSIONS'
                        ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40 shadow'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Navigation className="w-3.5 h-3.5" />
                    Missions
                  </button>
                  <button
                    onClick={() => setActiveTab('RESOURCES')}
                    className={`flex-1 py-2 px-2 rounded-lg text-xs font-semibold transition flex items-center justify-center gap-1.5 ${
                      activeTab === 'RESOURCES'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Shield className="w-3.5 h-3.5" />
                    Fleet
                  </button>
                  <button
                    onClick={() => setActiveTab('ALERTS')}
                    className={`flex-1 py-2 px-2 rounded-lg text-xs font-semibold transition flex items-center justify-center gap-1.5 relative ${
                      activeTab === 'ALERTS'
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 shadow'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <AlertOctagon className="w-3.5 h-3.5" />
                    Alerts
                    {overview.summary.unacknowledged_alerts > 0 && (
                      <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping absolute top-1 right-1" />
                    )}
                  </button>
                </div>

                {/* Tab Body */}
                <div className="flex-1 overflow-hidden">
                  {activeTab === 'QUEUE' && (
                    <IncidentPriorityQueue
                      queue={overview.priority_queue}
                      selectedIncidentId={selectedIncidentId}
                      onSelectIncident={(id) => setSelectedIncidentId(id)}
                      onDispatchClick={handleDispatchIncident}
                      onOptimizeClick={handleOptimizeIncident}
                    />
                  )}
                  {activeTab === 'MISSIONS' && (
                    <ActiveMissionTable
                      missions={overview.active_missions}
                      onSelectMission={openMissionPanel}
                      onEvaluateReroute={openMissionPanel}
                    />
                  )}
                  {activeTab === 'RESOURCES' && <ResourceOverview resources={overview.resource_overview} />}
                  {activeTab === 'ALERTS' && (
                    <CommandAlertFeed alerts={overview.alerts} onAcknowledge={handleAcknowledgeAlert} />
                  )}
                </div>
              </div>
            </div>

            {/* Full Active Mission Table Grid at bottom */}
            <div className="mb-6">
              <ActiveMissionTable
                missions={overview.active_missions}
                onSelectMission={openMissionPanel}
                onEvaluateReroute={openMissionPanel}
              />
            </div>
          </>
        )}

        {/* Active Mission Live Telemetry & Dynamic Rerouting Modal */}
        {activeDispatchResponse && (
          <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="max-w-4xl w-full max-h-[90vh] overflow-y-auto">
              <ActiveMissionPanel
                dispatchData={activeDispatchResponse}
                onClose={() => {
                  setActiveDispatchResponse(null);
                  fetchOverview();
                }}
              />
            </div>
          </div>
        )}

        {/* Stage 8B Multi-Unit Resource Optimization Modal */}
        {activeOptimization && (
          <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="max-w-3xl w-full max-h-[90vh] overflow-y-auto">
              <ResourceOptimizationPanel
                optimization={activeOptimization}
                onClose={() => {
                  setActiveOptimization(null);
                  fetchOverview();
                }}
              />
            </div>
          </div>
        )}
      </div>
    </PageContainer>
  );
};

