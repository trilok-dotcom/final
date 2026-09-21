import React from 'react';
import type { SimulationEvent } from '../../types/simulation';
import { Activity } from 'lucide-react';

interface SimulationEventFeedProps {
  events: SimulationEvent[];
  onTriggerEvent?: (type: string) => void;
}

export const SimulationEventFeed: React.FC<SimulationEventFeedProps> = ({
  events,
  onTriggerEvent,
}) => {
  const formatSimTime = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const s = sec % 60;
    return `${mins.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const getEventBadge = (type: string) => {
    switch (type) {
      case 'ROUTE_DEGRADATION_INJECT':
      case 'LOW_CONFIDENCE':
      case 'HIGH_RISK':
        return 'bg-rose-950/80 text-rose-300 border-rose-800';
      case 'REROUTE_RECOMMENDATION':
      case 'OPERATOR_REROUTE_APPROVE':
        return 'bg-cyan-950/80 text-cyan-300 border-cyan-800';
      case 'OPTIMIZE_RESOURCES':
      case 'CREATE_DISPATCH':
        return 'bg-amber-950/80 text-amber-300 border-amber-800';
      case 'DISASTER_START':
      case 'NEW_INCIDENT':
        return 'bg-purple-950/80 text-purple-300 border-purple-800';
      case 'MISSION_COMPLETE':
        return 'bg-emerald-950/80 text-emerald-300 border-emerald-800';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="bg-slate-900/80 backdrop-blur border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col h-full min-h-[400px]">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-amber-500" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            SIMULATION EVENT CHRONOLOGY STREAM
          </h3>
        </div>
        <span className="text-[10px] font-mono text-slate-400 font-bold">{events.length} EVENTS</span>
      </div>

      {/* Inject Event Controls for Demonstration */}
      {onTriggerEvent && (
        <div className="mb-3 p-2 bg-slate-950 rounded-lg border border-slate-800 flex flex-wrap gap-1.5">
          <span className="text-[10px] font-mono font-bold text-slate-400 w-full uppercase mb-0.5">
            DEMONSTRATION HAZARD INJECTION TRIPPERS:
          </span>
          <button
            onClick={() => onTriggerEvent('LOW_CONFIDENCE')}
            className="px-2 py-1 bg-rose-950/80 hover:bg-rose-900 border border-rose-800 text-rose-300 text-[10px] font-mono font-bold rounded transition"
          >
            + LOW CONFIDENCE
          </button>
          <button
            onClick={() => onTriggerEvent('HIGH_RISK')}
            className="px-2 py-1 bg-rose-950/80 hover:bg-rose-900 border border-rose-800 text-rose-300 text-[10px] font-mono font-bold rounded transition"
          >
            + HIGH RISK
          </button>
          <button
            onClick={() => onTriggerEvent('ETA_INCREASE')}
            className="px-2 py-1 bg-amber-950/80 hover:bg-amber-900 border border-amber-800 text-amber-300 text-[10px] font-mono font-bold rounded transition"
          >
            + ETA DELAY
          </button>
          <button
            onClick={() => onTriggerEvent('NEW_INCIDENT')}
            className="px-2 py-1 bg-purple-950/80 hover:bg-purple-900 border border-purple-800 text-purple-300 text-[10px] font-mono font-bold rounded transition"
          >
            + NEW INCIDENT
          </button>
        </div>
      )}

      {/* Events List */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-1 max-h-[320px]">
        {events.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs font-mono">
            No events logged yet. Click START to run simulation timeline.
          </div>
        ) : (
          events.map((ev) => (
            <div
              key={ev.id}
              className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-lg text-xs space-y-1 hover:border-slate-700 transition"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono font-bold text-amber-400 text-[11px]">
                  [T+{formatSimTime(ev.simulated_time)}]
                </span>
                <span
                  className={`text-[9px] font-mono font-bold uppercase px-2 py-0.5 rounded border ${getEventBadge(
                    ev.event_type
                  )}`}
                >
                  {ev.event_type.replace('_', ' ')}
                </span>
              </div>
              <div className="font-bold text-slate-200">{ev.title}</div>
              {ev.description && <div className="text-[11px] text-slate-400">{ev.description}</div>}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
