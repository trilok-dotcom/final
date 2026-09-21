import React from 'react';
import { Navigation, AlertTriangle } from 'lucide-react';

interface SimulationMissionPanelProps {
  missions: any[];
  onApproveReroute?: (dispatchId: string) => void;
}

export const SimulationMissionPanel: React.FC<SimulationMissionPanelProps> = ({
  missions,
  onApproveReroute,
}) => {
  return (
    <div className="bg-slate-900/80 backdrop-blur border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col h-full min-h-[400px]">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
        <div className="flex items-center gap-2">
          <Navigation className="w-4 h-4 text-blue-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            ACTIVE SIMULATION RESPONSE MISSIONS
          </h3>
        </div>
        <span className="text-[10px] font-mono text-slate-400 font-bold">{missions.length} MISSIONS</span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2.5 max-h-[360px]">
        {missions.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs font-mono">
            No active simulation dispatches yet. Timeline will initiate automatic dispatch at T+25s.
          </div>
        ) : (
          missions.map((m) => {
            const isDegraded = m.health_status === 'DEGRADED' || m.health_status === 'CRITICAL';

            return (
              <div
                key={m.id || m.dispatch_id}
                className="p-3 bg-slate-950/80 border border-slate-800 hover:border-slate-700 rounded-lg text-xs space-y-2 transition"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-slate-200 text-xs">
                    {m.rescue_unit_code || m.unit_code || 'SIM-UNIT'} → {m.incident_code || 'SIM-INC'}
                  </span>
                  <span
                    className={`text-[9px] font-mono font-bold uppercase px-2 py-0.5 rounded border ${
                      m.status === 'COMPLETED'
                        ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                        : 'bg-cyan-950 text-cyan-300 border-cyan-800 animate-pulse'
                    }`}
                  >
                    {m.status}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-400">
                  <div>
                    DIST REMAINING:{' '}
                    <span className="text-slate-200 font-bold">
                      {m.distance_meters ? `${(m.distance_meters / 1000).toFixed(1)} km` : '1.2 km'}
                    </span>
                  </div>
                  <div>
                    ETA:{' '}
                    <span className="text-slate-200 font-bold">
                      {m.estimated_duration_seconds ? `${Math.round(m.estimated_duration_seconds / 60)} mins` : '3 mins'}
                    </span>
                  </div>
                </div>

                {/* Route Health Alert Banner */}
                {isDegraded && (
                  <div className="p-2 bg-rose-950/40 border border-rose-500/50 rounded flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 text-rose-300 font-mono text-[10px] font-bold">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>⚠ AI RE-ROUTE RECOMMENDED</span>
                    </div>
                    {onApproveReroute && (
                      <button
                        onClick={() => onApproveReroute(m.id || m.dispatch_id)}
                        className="px-2.5 py-1 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold font-mono text-[10px] rounded uppercase transition shadow"
                      >
                        [ ACCEPT AI RE-ROUTE ]
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
