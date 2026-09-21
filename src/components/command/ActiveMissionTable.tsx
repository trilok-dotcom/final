import React from 'react';
import { Navigation, RefreshCw, Eye } from 'lucide-react';
import type { CommandActiveMission } from '../../types/commandCenter';

interface ActiveMissionTableProps {
  missions: CommandActiveMission[];
  onSelectMission: (dispatchId: string) => void;
  onEvaluateReroute: (dispatchId: string) => void;
}

export const ActiveMissionTable: React.FC<ActiveMissionTableProps> = ({
  missions,
  onSelectMission,
  onEvaluateReroute,
}) => {
  const getHealthBadge = (healthStatus: string) => {
    switch (healthStatus.toUpperCase()) {
      case 'DEGRADED':
      case 'CRITICAL':
        return 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse';
      case 'WARNING':
      case 'UNSTABLE':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
      case 'HEALTHY':
      default:
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case 'EN_ROUTE':
        return 'bg-blue-500/20 text-blue-300 border-blue-500/40';
      case 'ON_SCENE':
        return 'bg-purple-500/20 text-purple-300 border-purple-500/40';
      case 'PENDING':
      default:
        return 'bg-slate-500/20 text-slate-300 border-slate-500/40';
    }
  };

  return (
    <div className="bg-slate-900/80 backdrop-blur border border-slate-800 rounded-xl p-4 flex flex-col h-full shadow-lg">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
        <div className="flex items-center gap-2">
          <Navigation className="w-5 h-5 text-blue-400" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
            Active Mission Telemetry & Route Health (Stage 7C / 8C)
          </h2>
        </div>
        <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
          {missions.length} Missions Active
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-950/60 text-slate-400 uppercase font-mono text-[10px] border-b border-slate-800">
            <tr>
              <th className="py-2.5 px-3">Unit</th>
              <th className="py-2.5 px-3">Incident</th>
              <th className="py-2.5 px-3">Mission Status</th>
              <th className="py-2.5 px-3">Distance & ETA</th>
              <th className="py-2.5 px-3">Route Health</th>
              <th className="py-2.5 px-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {missions.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center py-8 text-slate-500 text-xs">
                  No active missions currently en-route.
                </td>
              </tr>
            ) : (
              missions.map((m) => (
                <tr key={m.dispatch_id} className="hover:bg-slate-800/40 transition">
                  <td className="py-3 px-3">
                    <div className="font-semibold text-slate-100">{m.unit_name}</div>
                    <div className="text-[10px] text-slate-400 uppercase tracking-wider">{m.unit_type}</div>
                  </td>
                  <td className="py-3 px-3">
                    <div className="font-medium text-slate-200 max-w-[180px] truncate">{m.incident_title}</div>
                    <div className="text-[10px] text-slate-400 capitalize">{m.incident_type} • {m.incident_severity}</div>
                  </td>
                  <td className="py-3 px-3">
                    <span className={`px-2 py-0.5 rounded border text-[10px] uppercase font-semibold ${getStatusBadge(m.status)}`}>
                      {m.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="py-3 px-3 font-mono text-slate-300">
                    <div>{m.distance_remaining_km != null ? `${m.distance_remaining_km.toFixed(1)} km` : '--'}</div>
                    <div className="text-[10px] text-slate-400">
                      {m.eta_seconds != null ? `${Math.round(m.eta_seconds / 60)} mins` : '--'}
                    </div>
                  </td>
                  <td className="py-3 px-3">
                    <div className="flex items-center gap-1.5">
                      <span className={`px-2 py-0.5 rounded border text-[10px] uppercase font-semibold ${getHealthBadge(m.health_status)}`}>
                        {m.health_status}
                      </span>
                      {m.route_confidence != null && (
                        <span className="text-[10px] font-mono text-slate-400">
                          {(m.route_confidence * 100).toFixed(0)}% AI
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-3 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => onSelectMission(m.dispatch_id)}
                        className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded transition"
                        title="View Live Telemetry Map"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => onEvaluateReroute(m.dispatch_id)}
                        className="px-2 py-1 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 rounded text-[10px] font-semibold transition flex items-center gap-1"
                        title="Evaluate Stage 8C Dynamic Rerouting"
                      >
                        <RefreshCw className="w-3 h-3" />
                        Reroute
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
