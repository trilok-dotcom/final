import React from 'react';
import type { SimulationSession } from '../../types/simulation';
import {
  Play,
  Pause,
  Square,
  FastForward,
  RotateCcw,
  Clock,
} from 'lucide-react';

interface SimulationControlsProps {
  session: SimulationSession;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onStep: () => void;
  onSetSpeed: (speed: number) => void;
  onReset: () => void;
  loading?: boolean;
}

export const SimulationControls: React.FC<SimulationControlsProps> = ({
  session,
  onStart,
  onPause,
  onResume,
  onStop,
  onStep,
  onSetSpeed,
  onReset,
  loading,
}) => {
  const isRunning = session.status === 'RUNNING';
  const isPaused = session.status === 'PAUSED';
  const isCreated = session.status === 'CREATED';
  const isCompleted = session.status === 'COMPLETED';

  const formatSimTime = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const s = sec % 60;
    return `${mins.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const getStatusBadgeClass = (st: string) => {
    switch (st) {
      case 'RUNNING':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40 animate-pulse';
      case 'PAUSED':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      case 'COMPLETED':
        return 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40';
      case 'STOPPED':
        return 'bg-rose-500/20 text-rose-400 border-rose-500/40';
      case 'CREATED':
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="bg-slate-900/90 backdrop-blur border border-slate-800 rounded-xl p-4 shadow-xl flex flex-col md:flex-row items-center justify-between gap-4">
      {/* Left Status & Virtual Clock */}
      <div className="flex items-center gap-4 w-full md:w-auto justify-between md:justify-start">
        <div className="flex items-center gap-2">
          <Clock className="w-5 h-5 text-amber-400" />
          <div>
            <div className="text-[10px] font-mono text-slate-400 uppercase font-bold">VIRTUAL SIMULATION CLOCK</div>
            <div className="text-xl font-mono font-bold text-slate-100 tracking-wider">
              T+{formatSimTime(session.simulation_time)}
            </div>
          </div>
        </div>

        <div className="h-8 w-px bg-slate-800 hidden md:block" />

        <div className="flex items-center gap-2">
          <span
            className={`px-3 py-1 rounded-lg text-xs font-mono font-bold uppercase border ${getStatusBadgeClass(
              session.status
            )}`}
          >
            ● {session.status}
          </span>
          <span className="text-xs font-mono text-slate-400">
            SEED: <span className="text-amber-400 font-bold">{session.seed}</span>
          </span>
        </div>
      </div>

      {/* Center Playback Controls */}
      <div className="flex items-center gap-2">
        {isCreated && (
          <button
            onClick={onStart}
            disabled={loading}
            className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold uppercase tracking-wider transition shadow-lg"
          >
            <Play className="w-4 h-4" />
            START
          </button>
        )}

        {isRunning && (
          <button
            onClick={onPause}
            disabled={loading}
            className="flex items-center gap-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-bold uppercase tracking-wider transition shadow-lg"
          >
            <Pause className="w-4 h-4" />
            PAUSE
          </button>
        )}

        {isPaused && (
          <button
            onClick={onResume}
            disabled={loading}
            className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold uppercase tracking-wider transition shadow-lg"
          >
            <Play className="w-4 h-4" />
            RESUME
          </button>
        )}

        {(isRunning || isPaused) && (
          <button
            onClick={onStop}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 bg-rose-950/80 hover:bg-rose-900 border border-rose-800 text-rose-300 rounded-lg text-xs font-bold uppercase tracking-wider transition"
          >
            <Square className="w-4 h-4" />
            STOP
          </button>
        )}

        <button
          onClick={onStep}
          disabled={loading || isCompleted}
          className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 rounded-lg text-xs font-bold uppercase tracking-wider transition"
          title="Advance Virtual Clock by 5 Seconds"
        >
          <FastForward className="w-4 h-4 text-cyan-400" />
          STEP (+5s)
        </button>

        <button
          onClick={onReset}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-rose-950/40 border border-slate-700 hover:border-rose-700 text-slate-400 hover:text-rose-300 rounded-lg text-xs font-bold uppercase tracking-wider transition"
          title="Reset Simulation Data"
        >
          <RotateCcw className="w-4 h-4" />
          RESET
        </button>
      </div>

      {/* Right Speed Multipliers */}
      <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800">
        <span className="text-[10px] font-mono text-slate-400 font-bold px-2 uppercase">SPEED:</span>
        {[1, 2, 5, 10].map((sp) => (
          <button
            key={sp}
            onClick={() => onSetSpeed(sp)}
            className={`py-1 px-2 text-xs font-mono font-bold rounded transition ${
              session.speed === sp
                ? 'bg-amber-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {sp}x
          </button>
        ))}
      </div>
    </div>
  );
};
