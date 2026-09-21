import React from 'react';
import { RefreshCw } from 'lucide-react';
import type { EvaluationOverview } from '../../types/evaluation';

interface Props {
  overview: EvaluationOverview | null;
  onRunReroutingEval: () => void;
  loading: boolean;
}

export const ReroutingMetricsPanel: React.FC<Props> = ({ overview, onRunReroutingEval, loading }) => {
  const r = overview?.rerouting;
  const isEvaluated = r?.status === 'EVALUATED';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl mb-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
        <div className="flex items-center gap-2">
          <RefreshCw className="w-5 h-5 text-amber-400" />
          <h2 className="text-lg font-bold text-white">7. Dynamic AI Re-Routing Performance</h2>
        </div>
        <button
          onClick={onRunReroutingEval}
          disabled={loading}
          className="px-3 py-1.5 rounded-md bg-amber-600/20 text-amber-300 hover:bg-amber-600/30 border border-amber-500/30 text-xs font-semibold transition disabled:opacity-50"
        >
          {loading ? 'Evaluating...' : 'Run Rerouting Evaluation'}
        </button>
      </div>

      {!isEvaluated ? (
        <div className="bg-slate-950/60 border border-dashed border-slate-800 rounded-lg p-6 text-center text-slate-400 text-sm">
          No rerouting evaluation data recorded. Click <span className="text-amber-400 font-semibold">Run Rerouting Evaluation</span> to compute adaptation metrics.
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Degradation Events</div>
            <div className="text-2xl font-bold text-amber-400 font-mono">{r.degradation_events}</div>
            <div className="text-xs text-slate-400 mt-1">Hazard / Low-confidence warnings</div>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Reroutes Approved</div>
            <div className="text-2xl font-bold text-emerald-400 font-mono">{r.approved} / {r.recommendations}</div>
            <div className="text-xs text-slate-400 mt-1">Operator-approved changes</div>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Avg Health Gain</div>
            <div className="text-2xl font-bold text-emerald-400 font-mono">+{r.average_health_improvement} pts</div>
            <div className="text-xs text-slate-400 mt-1">Post-reroute recovery</div>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Avg ETA Delta</div>
            <div className="text-2xl font-bold text-blue-400 font-mono">{r.average_eta_change_s} s</div>
            <div className="text-xs text-slate-400 mt-1">Travel time impact</div>
          </div>
        </div>
      )}
    </div>
  );
};
