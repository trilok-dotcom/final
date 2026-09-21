import React from 'react';
import { Truck } from 'lucide-react';
import type { EvaluationOverview } from '../../types/evaluation';

interface Props {
  overview: EvaluationOverview | null;
  onRunResourcesEval: () => void;
  loading: boolean;
}

export const ResourceMetricsPanel: React.FC<Props> = ({ overview, onRunResourcesEval, loading }) => {
  const res = overview?.resources;
  const isEvaluated = res?.status === 'EVALUATED';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl mb-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
        <div className="flex items-center gap-2">
          <Truck className="w-5 h-5 text-purple-400" />
          <h2 className="text-lg font-bold text-white">5. Resource Optimization & Fleet Utilization</h2>
        </div>
        <button
          onClick={onRunResourcesEval}
          disabled={loading}
          className="px-3 py-1.5 rounded-md bg-purple-600/20 text-purple-300 hover:bg-purple-600/30 border border-purple-500/30 text-xs font-semibold transition disabled:opacity-50"
        >
          {loading ? 'Evaluating...' : 'Run Resource Evaluation'}
        </button>
      </div>

      {!isEvaluated ? (
        <div className="bg-slate-950/60 border border-dashed border-slate-800 rounded-lg p-6 text-center text-slate-400 text-sm">
          No resource evaluation data recorded. Click <span className="text-purple-400 font-semibold">Run Resource Evaluation</span> to compute utilization metrics.
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Total Rescue Fleet</div>
            <div className="text-2xl font-bold text-white font-mono">{res.total_units} units</div>
            <div className="text-xs text-slate-400 mt-1">Multi-capability fleet</div>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Fleet Utilization</div>
            <div className="text-2xl font-bold text-purple-400 font-mono">{res.utilization_percent}%</div>
            <div className="text-xs text-slate-400 mt-1">Active assignment ratio</div>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Optimization Runs</div>
            <div className="text-2xl font-bold text-blue-400 font-mono">{res.optimization_runs}</div>
            <div className="text-xs text-slate-400 mt-1">Stage 8B allocations</div>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Avg Optimization Score</div>
            <div className="text-2xl font-bold text-emerald-400 font-mono">{res.average_optimization_score} / 100</div>
            <div className="text-xs text-slate-400 mt-1">6-factor scoring</div>
          </div>
        </div>
      )}
    </div>
  );
};
