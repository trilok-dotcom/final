import React from 'react';
import { Activity } from 'lucide-react';
import type { EvaluationOverview } from '../../types/evaluation';

interface Props {
  overview: EvaluationOverview | null;
  onRunMissionsEval: () => void;
  loading: boolean;
}

export const MissionMetricsPanel: React.FC<Props> = ({ overview, onRunMissionsEval, loading }) => {
  const m = overview?.missions;
  const isEvaluated = m?.status === 'EVALUATED';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl mb-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-emerald-400" />
          <h2 className="text-lg font-bold text-white">6. Dispatch Latency & Live Mission Execution</h2>
        </div>
        <button
          onClick={onRunMissionsEval}
          disabled={loading}
          className="px-3 py-1.5 rounded-md bg-emerald-600/20 text-emerald-300 hover:bg-emerald-600/30 border border-emerald-500/30 text-xs font-semibold transition disabled:opacity-50"
        >
          {loading ? 'Evaluating...' : 'Run Mission Evaluation'}
        </button>
      </div>

      {!isEvaluated ? (
        <div className="bg-slate-950/60 border border-dashed border-slate-800 rounded-lg p-6 text-center text-slate-400 text-sm">
          No mission evaluation data recorded. Click <span className="text-emerald-400 font-semibold">Run Mission Evaluation</span> to evaluate telemetry & latency metrics.
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Total Missions</div>
            <div className="text-2xl font-bold text-white font-mono">{m.total_dispatches}</div>
            <div className="text-xs text-emerald-400 mt-1">Completed: {m.completed}</div>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Avg Dispatch Latency</div>
            <div className="text-2xl font-bold text-emerald-400 font-mono">{m.average_dispatch_latency_s} s</div>
            <div className="text-xs text-slate-400 mt-1">Incident -&gt; Dispatch timestamp</div>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Avg Mission Duration</div>
            <div className="text-2xl font-bold text-blue-400 font-mono">{m.average_duration_s} s</div>
            <div className="text-xs text-slate-400 mt-1">Dispatched -&gt; Completed</div>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Telemetry Status</div>
            <div className="text-2xl font-bold text-purple-400 font-mono">Stage 7C</div>
            <div className="text-xs text-slate-400 mt-1">WebSocket Live Feed</div>
          </div>
        </div>
      )}
    </div>
  );
};
