import React from 'react';
import { Route } from 'lucide-react';
import type { EvaluationOverview } from '../../types/evaluation';

interface Props {
  overview: EvaluationOverview | null;
  onRunRoutingEval: () => void;
  loading: boolean;
}

export const RoutingMetricsPanel: React.FC<Props> = ({ overview, onRunRoutingEval, loading }) => {
  const r = overview?.routing;
  const isEvaluated = r?.status === 'EVALUATED';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl mb-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
        <div className="flex items-center gap-2">
          <Route className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-bold text-white">4. Emergency Routing & Health Evaluation</h2>
        </div>
        <button
          onClick={onRunRoutingEval}
          disabled={loading}
          className="px-3 py-1.5 rounded-md bg-blue-600/20 text-blue-300 hover:bg-blue-600/30 border border-blue-500/30 text-xs font-semibold transition disabled:opacity-50"
        >
          {loading ? 'Evaluating...' : 'Run Routing Evaluation'}
        </button>
      </div>

      {!isEvaluated ? (
        <div className="bg-slate-950/60 border border-dashed border-slate-800 rounded-lg p-6 text-center text-slate-400 text-sm">
          No routing evaluation data recorded. Click <span className="text-blue-400 font-semibold">Run Routing Evaluation</span> to measure route parameters.
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Routes Evaluated</div>
            <div className="text-2xl font-bold text-white font-mono">{r.routes_evaluated}</div>
            <div className="text-xs text-emerald-400 mt-1">Success Rate: {r.success_rate}%</div>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Avg Distance & ETA</div>
            <div className="text-2xl font-bold text-blue-400 font-mono">{r.average_distance_m} m</div>
            <div className="text-xs text-slate-400 mt-1">Avg ETA: {r.average_eta_s} seconds</div>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">AI Route Confidence</div>
            <div className="text-2xl font-bold text-purple-400 font-mono">{r.average_confidence}</div>
            <div className="text-xs text-slate-400 mt-1">Probability map weight</div>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Avg Route Health</div>
            <div className="text-2xl font-bold text-emerald-400 font-mono">{r.average_route_health} / 100</div>
            <div className="text-xs text-slate-400 mt-1">Stage 8C Health Score</div>
          </div>
        </div>
      )}
    </div>
  );
};
