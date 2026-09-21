import React, { useState, useEffect } from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { IncidentCard } from '../components/incidents/IncidentCard';
import { IncidentStats } from '../components/incidents/IncidentStats';
import { ActiveMissionPanel } from '../components/dispatch/ActiveMissionPanel';
import { getIncidents, createIncident, resolveIncident } from '../services/incidents';
import { dispatchIncident } from '../services/dispatch';
import type { Incident } from '../types/incident';
import type { DispatchResponse } from '../types/dispatch';
import { analyzeIncident } from '../services/intelligence';
import type { IncidentIntelligence } from '../types/intelligence';
import { IncidentIntelligencePanel } from '../components/incidents/IncidentIntelligencePanel';
import { optimizeIncidentResources } from '../services/resourceOptimization';
import type { ResourceOptimizationResponse } from '../types/resourceOptimization';
import { ResourceOptimizationPanel } from '../components/incidents/ResourceOptimizationPanel';
import { AlertTriangle, Search, Filter, Plus, Loader2, X, Zap, Brain, Cpu } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const IncidentsPage: React.FC = () => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Active Dispatch Mission Modal
  const [activeDispatch, setActiveDispatch] = useState<DispatchResponse | null>(null);
  const [dispatchingId, setDispatchingId] = useState<string | null>(null);

  // AI Intelligence Modal
  const [selectedIntelligence, setSelectedIntelligence] = useState<IncidentIntelligence | null>(null);
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);

  // AI Resource Optimization Modal
  const [selectedOptimization, setSelectedOptimization] = useState<ResourceOptimizationResponse | null>(null);
  const [optimizingId, setOptimizingId] = useState<string | null>(null);

  // Form State for new incident
  const [formType, setFormType] = useState('FIRE');
  const [formSeverity, setFormSeverity] = useState('CRITICAL');
  const [formLat, setFormLat] = useState('12.9716');
  const [formLng, setFormLng] = useState('77.5946');
  const [formLocation, setFormLocation] = useState('MG Road Commercial Zone');
  const [formDesc, setFormDesc] = useState('Commercial structure emergency reported to dispatch.');

  const navigate = useNavigate();

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await getIncidents();
      setIncidents(data);
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateIncident = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await createIncident({
        incident_type: formType,
        severity: formSeverity,
        latitude: parseFloat(formLat),
        longitude: parseFloat(formLng),
        location_name: formLocation,
        description: formDesc,
      });
      setIsModalOpen(false);
      await loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create incident.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleTriggerDispatch = async (incidentId: string) => {
    setDispatchingId(incidentId);
    try {
      const res = await dispatchIncident(incidentId);
      setActiveDispatch(res);
      await loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to trigger automatic rescue dispatch.');
    } finally {
      setDispatchingId(null);
    }
  };

  const handleResolve = async (id: string) => {
    try {
      await resolveIncident(id);
      await loadData();
    } catch (_err) {
      alert('Failed to resolve incident');
    }
  };

  const handleAnalyzeIncident = async (incidentId: string) => {
    setAnalyzingId(incidentId);
    try {
      const intel = await analyzeIncident(incidentId);
      setSelectedIntelligence(intel);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to execute AI incident analysis.');
    } finally {
      setAnalyzingId(null);
    }
  };

  const handleOptimizeResources = async (incidentId: string) => {
    setOptimizingId(incidentId);
    try {
      const opt = await optimizeIncidentResources(incidentId);
      setSelectedOptimization(opt);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to calculate resource optimization.');
    } finally {
      setOptimizingId(null);
    }
  };

  const filteredIncidents = incidents.filter((incident) => {
    const sev = (incident.severity || 'low').toString().toLowerCase();
    const st = (incident.status || 'reported').toString().toLowerCase();
    const title = (incident.location_name || incident.title || '').toLowerCase();
    const code = (incident.incident_code || incident.code || '').toLowerCase();
    const desc = (incident.description || '').toLowerCase();

    const matchesSeverity = filterSeverity === 'all' || sev === filterSeverity.toLowerCase();
    const matchesStatus = filterStatus === 'all' || st === filterStatus.toLowerCase();
    const matchesSearch =
      title.includes(searchQuery.toLowerCase()) ||
      code.includes(searchQuery.toLowerCase()) ||
      desc.includes(searchQuery.toLowerCase());

    return matchesSeverity && matchesStatus && matchesSearch;
  });

  return (
    <PageContainer>
      <div className="flex-1 flex flex-col h-full overflow-y-auto bg-[#090d16] p-6 space-y-6 select-none font-sans">
        {/* Header Title */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-800 pb-4 gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5 text-red-500" />
              <h2 className="font-mono font-bold text-lg tracking-wider text-slate-100 uppercase">
                INCIDENT MANAGEMENT DISPATCH
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Live disaster events, automatic rescue unit selection, AI Dijkstra routing, and mission control.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
              className="py-2 px-3 bg-red-600 hover:bg-red-500 text-white font-mono font-bold text-xs rounded uppercase flex items-center space-x-1.5 transition-colors shadow-lg shadow-red-600/20"
            >
              <Plus className="w-4 h-4" />
              <span>REPORT INCIDENT</span>
            </button>
            <div className="hidden sm:block">
              <IncidentStats />
            </div>
          </div>
        </div>

        {/* Filter & Search Toolbar */}
        <div className="flex flex-col lg:flex-row items-center justify-between gap-4 bg-[#0b0f19] p-3 rounded-lg border border-slate-800">
          <div className="relative w-full lg:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by code, title, description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded pl-9 pr-3 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2 w-full lg:w-auto">
            <div className="flex items-center space-x-1">
              <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <span className="text-[11px] font-mono text-slate-400">SEVERITY:</span>
            </div>
            {['all', 'critical', 'high', 'medium', 'low'].map((sev) => (
              <button
                key={sev}
                type="button"
                onClick={() => setFilterSeverity(sev)}
                className={`px-2 py-0.5 rounded text-[11px] font-mono uppercase transition-colors shrink-0 ${
                  filterSeverity === sev
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold'
                    : 'text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800'
                }`}
              >
                {sev}
              </button>
            ))}

            <div className="h-4 w-px bg-slate-800 mx-1"></div>

            <div className="flex items-center space-x-1">
              <span className="text-[11px] font-mono text-slate-400">STATUS:</span>
            </div>
            {['all', 'reported', 'active', 'resolved'].map((st) => (
              <button
                key={st}
                type="button"
                onClick={() => setFilterStatus(st)}
                className={`px-2 py-0.5 rounded text-[11px] font-mono uppercase transition-colors shrink-0 ${
                  filterStatus === st
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold'
                    : 'text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        {/* Incident List Grid */}
        {loading ? (
          <div className="py-12 flex items-center justify-center space-x-2 text-cyan-400 font-mono text-xs">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>LOADING EMERGENCY INCIDENTS FROM DATABASE...</span>
          </div>
        ) : filteredIncidents.length === 0 ? (
          <div className="py-12 text-center text-slate-500 font-mono text-xs border border-dashed border-slate-800 rounded">
            NO MATCHING EMERGENCY INCIDENTS FOUND
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredIncidents.map((incident) => {
              const isDispatched = incident.status === 'DISPATCHING' || incident.status === 'ACTIVE' || incident.status === 'DISPATCHED' || Boolean(incident.assigned_unit_id);
              const isResolved = incident.status === 'RESOLVED';

              return (
                <div key={incident.id} className="relative group flex flex-col justify-between bg-[#0f172a]/60 border border-slate-800 rounded-lg p-4 font-sans space-y-3">
                  <IncidentCard
                    incident={incident}
                    onRouteIncident={() => navigate('/route-planning')}
                  />

                  {/* Action Buttons: Intelligence, Optimization & Auto Dispatch */}
                  <div className="pt-2 border-t border-slate-800/60 space-y-1.5 font-mono">
                    <div className="grid grid-cols-2 gap-1.5">
                      <button
                        type="button"
                        disabled={analyzingId === incident.id}
                        onClick={() => handleAnalyzeIncident(incident.id)}
                        className="py-1.5 px-2 bg-slate-900 hover:bg-slate-800 text-cyan-300 border border-cyan-800/60 font-bold text-[10px] rounded uppercase flex items-center justify-center space-x-1 transition-all cursor-pointer"
                      >
                        {analyzingId === incident.id ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <Brain className="w-3 h-3 text-cyan-400" />
                        )}
                        <span>INTELLIGENCE</span>
                      </button>

                      <button
                        type="button"
                        disabled={optimizingId === incident.id}
                        onClick={() => handleOptimizeResources(incident.id)}
                        className="py-1.5 px-2 bg-cyan-950/80 hover:bg-cyan-900/80 text-cyan-300 border border-cyan-700/60 font-bold text-[10px] rounded uppercase flex items-center justify-center space-x-1 transition-all cursor-pointer"
                      >
                        {optimizingId === incident.id ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <Cpu className="w-3 h-3 text-cyan-400" />
                        )}
                        <span>AI OPTIMIZE</span>
                      </button>
                    </div>

                    {!isResolved && !isDispatched && (
                      <button
                        type="button"
                        disabled={dispatchingId === incident.id}
                        onClick={() => handleTriggerDispatch(incident.id)}
                        className="w-full py-1.5 px-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-[11px] rounded uppercase flex items-center justify-center space-x-1 transition-all shadow-md cursor-pointer"
                      >
                        {dispatchingId === incident.id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-950" />
                        ) : (
                          <Zap className="w-3.5 h-3.5" />
                        )}
                        <span>SINGLE AUTO DISPATCH</span>
                      </button>
                    )}

                    {!isResolved && isDispatched && (
                      <div className="w-full py-1 px-2 bg-purple-950/40 border border-purple-800/60 text-purple-300 text-[10px] font-bold rounded flex items-center justify-between">
                        <span className="flex items-center space-x-1">
                          <Zap className="w-3 h-3 text-purple-400 animate-pulse" />
                          <span>DISPATCH ACTIVE</span>
                        </span>
                        <button
                          type="button"
                          onClick={() => handleResolve(incident.id)}
                          className="hover:text-emerald-400 text-[10px] underline uppercase"
                        >
                          RESOLVE
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* AI RESOURCE OPTIMIZATION MODAL */}
      {selectedOptimization && (
        <div className="fixed inset-0 z-[2000] bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-2xl w-full relative">
            <button
              type="button"
              onClick={() => setSelectedOptimization(null)}
              className="absolute top-3 right-3 z-10 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <ResourceOptimizationPanel
              optimization={selectedOptimization}
              onDispatchConfirmed={() => loadData()}
              onClose={() => setSelectedOptimization(null)}
            />
          </div>
        </div>
      )}

      {/* AI INCIDENT INTELLIGENCE MODAL */}
      {selectedIntelligence && (
        <div className="fixed inset-0 z-[2000] bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-xl w-full relative">
            <button
              type="button"
              onClick={() => setSelectedIntelligence(null)}
              className="absolute top-3 right-3 z-10 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <IncidentIntelligencePanel
              intelligence={selectedIntelligence}
              onClose={() => setSelectedIntelligence(null)}
            />
          </div>
        </div>
      )}

      {/* ACTIVE MISSION MODAL POPUP */}
      {activeDispatch && (
        <div className="fixed inset-0 z-[2000] bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-lg w-full relative">
            <button
              type="button"
              onClick={() => setActiveDispatch(null)}
              className="absolute top-3 right-3 z-10 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <ActiveMissionPanel
              dispatchData={activeDispatch}
              onStatusChange={() => {
                loadData();
              }}
            />
          </div>
        </div>
      )}

      {/* REPORT INCIDENT MODAL DIALOG */}
      {isModalOpen && (
        <div className="fixed inset-0 z-[2000] bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0b0f19] border border-slate-800 rounded-lg max-w-md w-full p-6 shadow-2xl space-y-4 font-sans">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-red-500" />
                <h3 className="font-mono font-bold text-sm text-slate-100 uppercase">
                  REPORT EMERGENCY INCIDENT
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateIncident} className="space-y-3 font-mono text-xs">
              <div>
                <label className="text-slate-400 block mb-1">INCIDENT TYPE</label>
                <select
                  value={formType}
                  onChange={(e) => setFormType(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="FIRE">FIRE</option>
                  <option value="MEDICAL">MEDICAL</option>
                  <option value="ACCIDENT">ACCIDENT</option>
                  <option value="FLOOD">FLOOD</option>
                  <option value="COLLAPSED_BUILDING">COLLAPSED BUILDING</option>
                  <option value="EARTHQUAKE">EARTHQUAKE</option>
                  <option value="MISSING_PERSON">MISSING PERSON</option>
                  <option value="HAZMAT">HAZMAT</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">SEVERITY TRIAGE</label>
                <select
                  value={formSeverity}
                  onChange={(e) => setFormSeverity(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="CRITICAL">CRITICAL (IMMEDIATE RESPONSE)</option>
                  <option value="HIGH">HIGH (URGENT)</option>
                  <option value="MEDIUM">MEDIUM (MODERATE)</option>
                  <option value="LOW">LOW (MONITOR)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-400 block mb-1">LATITUDE</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={formLat}
                    onChange={(e) => setFormLat(e.target.value)}
                    required
                    className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">LONGITUDE</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={formLng}
                    onChange={(e) => setFormLng(e.target.value)}
                    required
                    className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">LOCATION NAME</label>
                <input
                  type="text"
                  value={formLocation}
                  onChange={(e) => setFormLocation(e.target.value)}
                  placeholder="e.g. Sector 4 Bridge Exit"
                  required
                  className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">DESCRIPTION</label>
                <textarea
                  value={formDesc}
                  onChange={(e) => setFormDesc(e.target.value)}
                  rows={3}
                  className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="pt-2 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="py-2 px-4 bg-slate-800 text-slate-400 hover:text-white rounded uppercase"
                >
                  CANCEL
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="py-2 px-4 bg-red-600 hover:bg-red-500 text-white font-bold rounded uppercase flex items-center space-x-1.5"
                >
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <span>SUBMIT INCIDENT</span>}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </PageContainer>
  );
};
