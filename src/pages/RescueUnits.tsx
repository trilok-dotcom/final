import React, { useState, useEffect } from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { RescueUnitCard } from '../components/rescue/RescueUnitCard';
import { getRescueUnits, updateRescueUnitStatus, createRescueUnit } from '../services/rescueUnits';
import type { RescueUnit } from '../types/rescue';
import { ShieldCheck, Search, Filter, LayoutGrid, List, Loader2, Plus, X } from 'lucide-react';

export const RescueUnitsPage: React.FC = () => {
  const [units, setUnits] = useState<RescueUnit[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Form State for new rescue unit
  const [formCode, setFormCode] = useState('AMB-03');
  const [formName, setFormName] = useState('Metro Ambulance 03');
  const [formType, setFormType] = useState('AMBULANCE');
  const [formStatus, setFormStatus] = useState('AVAILABLE');
  const [formLat, setFormLat] = useState('12.9797');
  const [formLng, setFormLng] = useState('77.5834');
  const [formCrew, setFormCrew] = useState('3');
  const [formCaps, setFormCaps] = useState('medical, first_aid, patient_transport');

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await getRescueUnits();
      setUnits(data);
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleCreateUnit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const caps = formCaps.split(',').map((c) => c.trim()).filter(Boolean);
      await createRescueUnit({
        unit_code: formCode,
        name: formName,
        unit_type: formType,
        status: formStatus,
        latitude: parseFloat(formLat),
        longitude: parseFloat(formLng),
        crew_size: parseInt(formCrew, 10) || 1,
        capabilities: caps,
      });
      setIsModalOpen(false);
      await loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create rescue unit.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusChange = async (unitId: string, newStatus: string) => {
    try {
      await updateRescueUnitStatus(unitId, newStatus);
      await loadData();
    } catch {
      alert('Failed to update status');
    }
  };

  const filteredUnits = units.filter((unit) => {
    const st = (unit.status || 'available').toString().toLowerCase();
    const name = (unit.name || '').toLowerCase();
    const code = (unit.unit_code || unit.unitCode || '').toLowerCase();

    const matchesStatus = filterStatus === 'all' || st === filterStatus.toLowerCase();
    const matchesSearch = name.includes(searchQuery.toLowerCase()) || code.includes(searchQuery.toLowerCase());

    return matchesStatus && matchesSearch;
  });

  return (
    <PageContainer>
      <div className="flex-1 flex flex-col h-full overflow-y-auto bg-[#090d16] p-6 space-y-6 select-none font-sans">
        {/* Header Title */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <div className="flex items-center space-x-2">
              <ShieldCheck className="w-5 h-5 text-cyan-400" />
              <h2 className="font-mono font-bold text-lg tracking-wider text-slate-100 uppercase">
                RESCUE UNITS & ASSETS
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Active tactical teams, equipment readiness, SQLite database status, and deployment telemetry.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
              className="py-2 px-3 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-mono font-bold text-xs rounded uppercase flex items-center space-x-1.5 transition-colors shadow-lg shadow-cyan-600/20 cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>ADD RESCUE UNIT</span>
            </button>

            <div className="flex items-center space-x-1 bg-slate-900 p-1 rounded border border-slate-800">
              <button
                type="button"
                onClick={() => setViewMode('grid')}
                className={`p-1.5 rounded transition-colors ${
                  viewMode === 'grid' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Grid View"
              >
                <LayoutGrid className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => setViewMode('table')}
                className={`p-1.5 rounded transition-colors ${
                  viewMode === 'table' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Table View"
              >
                <List className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-col lg:flex-row items-center justify-between gap-4 bg-[#0b0f19] p-3 rounded-lg border border-slate-800">
          <div className="relative w-full lg:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by code, unit name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded pl-9 pr-3 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2 w-full lg:w-auto">
            <Filter className="w-4 h-4 text-slate-400 shrink-0" />
            <span className="text-[11px] font-mono text-slate-400">STATUS:</span>
            {['all', 'available', 'dispatched', 'en_route', 'on_scene', 'offline'].map((st) => (
              <button
                key={st}
                type="button"
                onClick={() => setFilterStatus(st)}
                className={`px-2.5 py-1 rounded text-xs font-mono uppercase transition-colors shrink-0 ${
                  filterStatus === st
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold'
                    : 'text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800'
                }`}
              >
                {st.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        {/* Grid or Table View */}
        {loading ? (
          <div className="py-12 flex items-center justify-center space-x-2 text-cyan-400 font-mono text-xs">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>LOADING RESCUE UNITS FROM DATABASE...</span>
          </div>
        ) : filteredUnits.length === 0 ? (
          <div className="py-12 text-center text-slate-500 font-mono text-xs border border-dashed border-slate-800 rounded">
            NO RESCUE UNITS FOUND
          </div>
        ) : viewMode === 'grid' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredUnits.map((unit) => (
              <RescueUnitCard key={unit.id} unit={unit} />
            ))}
          </div>
        ) : (
          /* Table View */
          <div className="bg-[#0b0f19] border border-slate-800 rounded-lg overflow-x-auto">
            <table className="w-full text-left border-collapse font-sans text-xs">
              <thead>
                <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-mono uppercase text-[11px]">
                  <th className="p-3">Unit Code</th>
                  <th className="p-3">Unit Name</th>
                  <th className="p-3">Type</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Coordinates</th>
                  <th className="p-3">Crew</th>
                  <th className="p-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-[11px] text-slate-300">
                {filteredUnits.map((unit) => {
                  const code = unit.unit_code || unit.unitCode || 'UNIT-01';
                  const type = unit.unit_type || unit.type || 'AMBULANCE';
                  const lat = unit.latitude ?? unit.location?.lat ?? 12.97;
                  const lng = unit.longitude ?? unit.location?.lng ?? 77.58;
                  const crew = unit.crew_size || unit.crewCount || 1;

                  return (
                    <tr key={unit.id} className="hover:bg-slate-900/40 transition-colors">
                      <td className="p-3 font-bold text-cyan-400">{code}</td>
                      <td className="p-3 font-sans font-semibold text-slate-100">{unit.name}</td>
                      <td className="p-3 uppercase text-slate-400">{type}</td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300 uppercase">
                          {unit.status.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="p-3 text-slate-400">
                        [{lat.toFixed(3)}, {lng.toFixed(3)}]
                      </td>
                      <td className="p-3">{crew} PERS</td>
                      <td className="p-3">
                        <select
                          value={unit.status}
                          onChange={(e) => handleStatusChange(unit.id, e.target.value)}
                          className="bg-slate-900 border border-slate-700 text-[10px] text-cyan-300 rounded px-1.5 py-0.5 focus:outline-none"
                        >
                          <option value="AVAILABLE">AVAILABLE</option>
                          <option value="EN_ROUTE">EN ROUTE</option>
                          <option value="ON_SCENE">ON SCENE</option>
                          <option value="RETURNING">RETURNING</option>
                          <option value="OFFLINE">OFFLINE</option>
                        </select>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ADD RESCUE UNIT MODAL */}
      {isModalOpen && (
        <div className="fixed inset-0 z-[2000] bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0b0f19] border border-slate-800 rounded-lg max-w-md w-full p-6 shadow-2xl space-y-4 font-sans">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <ShieldCheck className="w-4 h-4 text-cyan-400" />
                <h3 className="font-mono font-bold text-sm text-slate-100 uppercase">
                  ADD RESCUE UNIT ASSET
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

            <form onSubmit={handleCreateUnit} className="space-y-3 font-mono text-xs">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-400 block mb-1">UNIT CODE</label>
                  <input
                    type="text"
                    value={formCode}
                    onChange={(e) => setFormCode(e.target.value.toUpperCase())}
                    required
                    className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">UNIT TYPE</label>
                  <select
                    value={formType}
                    onChange={(e) => setFormType(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="AMBULANCE">AMBULANCE</option>
                    <option value="FIRE_TRUCK">FIRE TRUCK</option>
                    <option value="POLICE">POLICE</option>
                    <option value="RESCUE_TEAM">RESCUE TEAM</option>
                    <option value="DISASTER_RESPONSE">DISASTER RESPONSE</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">UNIT NAME</label>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  required
                  className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                />
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

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-400 block mb-1">CREW SIZE</label>
                  <input
                    type="number"
                    min="1"
                    value={formCrew}
                    onChange={(e) => setFormCrew(e.target.value)}
                    required
                    className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">STATUS</label>
                  <select
                    value={formStatus}
                    onChange={(e) => setFormStatus(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="AVAILABLE">AVAILABLE</option>
                    <option value="EN_ROUTE">EN ROUTE</option>
                    <option value="ON_SCENE">ON SCENE</option>
                    <option value="OFFLINE">OFFLINE</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">CAPABILITIES (COMMA SEPARATED)</label>
                <input
                  type="text"
                  value={formCaps}
                  onChange={(e) => setFormCaps(e.target.value)}
                  placeholder="medical, first_aid, patient_transport"
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
                  className="py-2 px-4 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded uppercase flex items-center space-x-1.5"
                >
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <span>ADD RESCUE UNIT</span>}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </PageContainer>
  );
};
