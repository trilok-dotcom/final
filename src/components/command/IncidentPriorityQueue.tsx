import React from 'react';
import { Zap, CheckCircle2, ShieldAlert, Cpu, ArrowUpRight, Activity } from 'lucide-react';
import type { CommandPriorityIncident } from '../../types/commandCenter';

interface IncidentPriorityQueueProps {
  queue: CommandPriorityIncident[];
  selectedIncidentId: string | null;
  onSelectIncident: (incidentId: string) => void;
  onDispatchClick: (incidentId: string) => void;
  onOptimizeClick: (incidentId: string) => void;
}

export const IncidentPriorityQueue: React.FC<IncidentPriorityQueueProps> = ({
  queue,
  selectedIncidentId,
  onSelectIncident,
  onDispatchClick,
  onOptimizeClick,
}) => {
  const getSeverityBadge = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-red-500/20 text-red-400 border-red-500/40';
      case 'HIGH':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      case 'MEDIUM':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/40';
    }
  };

  return (
    <div className="bg-slate-900/80 backdrop-blur border border-slate-800 rounded-xl p-4 flex flex-col h-full shadow-lg">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-amber-400" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
            Incident Priority Queue (Stage 8A)
          </h2>
        </div>
        <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
          {queue.length} Total Active
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-1 max-h-[520px]">
        {queue.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-xs">
            No active incidents in priority queue.
          </div>
        ) : (
          queue.map((item, index) => {
            const inc = item.incident;
            const isSelected = selectedIncidentId === inc.id;

            return (
              <div
                key={inc.id}
                onClick={() => onSelectIncident(inc.id)}
                className={`p-3 rounded-lg border transition cursor-pointer ${
                  isSelected
                    ? 'bg-slate-800/90 border-amber-500/70 shadow-md ring-1 ring-amber-500/30'
                    : 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700 hover:bg-slate-800/40'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
                      #{index + 1}
                    </span>
                    <h3 className="text-sm font-semibold text-slate-100 line-clamp-1">{inc.title}</h3>
                  </div>
                  <span
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded border uppercase tracking-wider ${getSeverityBadge(
                      inc.severity
                    )}`}
                  >
                    {inc.severity}
                  </span>
                </div>

                <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
                  <span className="capitalize text-slate-300 font-medium">{inc.type}</span>
                  <div className="flex items-center gap-1.5 font-mono text-[11px] text-amber-300">
                    <Activity className="w-3.5 h-3.5 text-amber-400" />
                    <span>Intel Score: {(item.intelligence_score * 100).toFixed(0)}</span>
                  </div>
                </div>

                {/* Status / Mission tag */}
                <div className="mt-2 flex items-center justify-between pt-2 border-t border-slate-800/60 text-xs">
                  {item.has_active_mission ? (
                    <span className="flex items-center gap-1 text-emerald-400 font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Mission Assigned
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-rose-400 font-medium">
                      <ShieldAlert className="w-3.5 h-3.5" />
                      Unassigned
                    </span>
                  )}

                  <div className="flex items-center gap-2">
                    {!item.has_active_mission && (
                      <>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onOptimizeClick(inc.id);
                          }}
                          className="px-2 py-1 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 rounded text-[10px] font-semibold transition flex items-center gap-1"
                          title="Stage 8B Resource Optimization"
                        >
                          <Cpu className="w-3 h-3" />
                          Optimize
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDispatchClick(inc.id);
                          }}
                          className="px-2 py-1 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/40 text-blue-300 rounded text-[10px] font-semibold transition flex items-center gap-1"
                        >
                          Dispatch
                          <ArrowUpRight className="w-3 h-3" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
