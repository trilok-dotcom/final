import React from 'react';
import type { SimulationEvent } from '../../types/simulation';
import { CheckCircle2, Clock, PlayCircle } from 'lucide-react';

interface SimulationTimelineProps {
  events: SimulationEvent[];
  currentTime: number;
}

export const SimulationTimeline: React.FC<SimulationTimelineProps> = ({ events, currentTime }) => {
  const maxTime = Math.max(180, ...events.map((e) => e.simulated_time));
  const progressPct = Math.min(100, Math.round((currentTime / maxTime) * 100));

  const formatSimTime = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const s = sec % 60;
    return `${mins.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="bg-slate-900/80 backdrop-blur border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col space-y-3">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            SIMULATION EXERCISE TIMELINE PROGRESS
          </h3>
        </div>
        <span className="text-xs font-mono font-bold text-cyan-400">
          {progressPct}% COMPLETED (T+{formatSimTime(currentTime)} / T+{formatSimTime(maxTime)})
        </span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800 relative">
        <div
          className="bg-gradient-to-r from-amber-500 via-cyan-500 to-emerald-500 h-full transition-all duration-300"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Event Steps Timeline Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-11 gap-1.5 pt-1">
        {events.map((ev) => {
          const isExecuted = ev.status === 'EXECUTED';
          const isCurrent = currentTime >= ev.simulated_time && !isExecuted;

          return (
            <div
              key={ev.id}
              className={`p-2 rounded-lg border flex flex-col justify-between text-left transition ${
                isExecuted
                  ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-300'
                  : isCurrent
                  ? 'bg-amber-950/40 border-amber-500/60 text-amber-300 animate-pulse'
                  : 'bg-slate-950/60 border-slate-800 text-slate-400'
              }`}
            >
              <div className="flex items-center justify-between text-[10px] font-mono font-bold">
                <span>T+{formatSimTime(ev.simulated_time)}</span>
                {isExecuted ? (
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                ) : isCurrent ? (
                  <PlayCircle className="w-3 h-3 text-amber-400 animate-spin" />
                ) : (
                  <Clock className="w-3 h-3 text-slate-500" />
                )}
              </div>
              <div className="text-[10px] font-bold truncate mt-1" title={ev.title}>
                {ev.event_type.replace('_', ' ')}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
