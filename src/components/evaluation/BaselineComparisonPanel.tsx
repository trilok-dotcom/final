import React from 'react';
import { GitCompare } from 'lucide-react';
import type { EvaluationOverview } from '../../types/evaluation';

interface Props {
  overview: EvaluationOverview | null;
  onRunOsrmBaseline: () => void;
  onRunNearestUnitBaseline: () => void;
  loading: boolean;
}

export const BaselineComparisonPanel: React.FC<Props> = ({
  overview,
  onRunOsrmBaseline,
  onRunNearestUnitBaseline,
  loading,
}) => {
  const osrmData = overview?.baselines?.osrm_baseline;
  const nearestData = overview?.baselines?.nearest_unit_baseline;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl mb-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
        <div className="flex items-center gap-2">
          <GitCompare className="w-5 h-5 text-indigo-400" />
          <h2 className="text-lg font-bold text-white">9. Neutral Baseline Comparisons</h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onRunOsrmBaseline}
            disabled={loading}
            className="px-3 py-1.5 rounded-md bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600/30 border border-indigo-500/30 text-xs font-semibold transition disabled:opacity-50"
          >
            {loading ? 'Evaluating...' : 'Run Baseline A (OSRM)'}
          </button>
          <button
            onClick={onRunNearestUnitBaseline}
            disabled={loading}
            className="px-3 py-1.5 rounded-md bg-purple-600/20 text-purple-300 hover:bg-purple-600/30 border border-purple-500/30 text-xs font-semibold transition disabled:opacity-50"
          >
            {loading ? 'Evaluating...' : 'Run Baseline B (Nearest Unit)'}
          </button>
        </div>
      </div>

      <p className="text-slate-400 text-xs mb-6">
        Evaluates system capabilities side-by-side against standard baselines without making scientifically unsupported claims.
      </p>

      {/* Baseline A Table */}
      <div className="mb-6">
        <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider mb-3">
          Baseline A — AI Emergency Routing vs Standard OSRM Routing
        </h3>
        {!osrmData ? (
          <div className="bg-slate-950/60 border border-dashed border-slate-800 rounded-lg p-4 text-center text-slate-400 text-xs">
            Baseline A not evaluated yet. Click <span className="text-indigo-400 font-semibold">Run Baseline A (OSRM)</span> to compare.
          </div>
        ) : (
          <div className="overflow-x-auto bg-slate-950 border border-slate-800 rounded-lg">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-900 text-xs uppercase text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-4">Metric</th>
                  <th className="py-2.5 px-4 text-emerald-400 font-bold">RESQROUTE AI Routing</th>
                  <th className="py-2.5 px-4 text-indigo-400 font-bold">Standard OSRM Routing Baseline</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                <tr>
                  <td className="py-2.5 px-4 font-sans text-slate-400 font-semibold">Average Route Distance</td>
                  <td className="py-2.5 px-4 text-emerald-400 font-bold">{osrmData.ai_routing?.average_distance_m} m</td>
                  <td className="py-2.5 px-4 text-indigo-400 font-bold">{osrmData.osrm_baseline?.average_distance_m} m</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 font-sans text-slate-400 font-semibold">Average ETA</td>
                  <td className="py-2.5 px-4 text-emerald-400 font-bold">{osrmData.ai_routing?.average_eta_s} s</td>
                  <td className="py-2.5 px-4 text-indigo-400 font-bold">{osrmData.osrm_baseline?.average_eta_s} s</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 font-sans text-slate-400 font-semibold">Routing Success Rate</td>
                  <td className="py-2.5 px-4 text-emerald-400 font-bold">{osrmData.ai_routing?.success_rate_percent}%</td>
                  <td className="py-2.5 px-4 text-indigo-400 font-bold">{osrmData.osrm_baseline?.success_rate_percent}%</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 font-sans text-slate-400 font-semibold">Routing Latency</td>
                  <td className="py-2.5 px-4 text-emerald-400 font-bold">{osrmData.ai_routing?.average_latency_ms} ms</td>
                  <td className="py-2.5 px-4 text-indigo-400 font-bold">{osrmData.osrm_baseline?.average_latency_ms} ms</td>
                </tr>
              </tbody>
            </table>
            {osrmData.interpretation_note && (
              <div className="p-3 bg-slate-900/60 border-t border-slate-800 text-xs text-slate-400 italic">
                Note: {osrmData.interpretation_note}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Baseline B Table */}
      <div>
        <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider mb-3">
          Baseline B — Stage 8B Multi-Factor Optimization vs Nearest Available Unit
        </h3>
        {!nearestData || nearestData.status === 'NOT_EVALUATED' ? (
          <div className="bg-slate-950/60 border border-dashed border-slate-800 rounded-lg p-4 text-center text-slate-400 text-xs">
            Baseline B not evaluated yet or insufficient comparable data. Click{' '}
            <span className="text-purple-400 font-semibold">Run Baseline B (Nearest Unit)</span> to evaluate.
          </div>
        ) : (
          <div className="overflow-x-auto bg-slate-950 border border-slate-800 rounded-lg">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-900 text-xs uppercase text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-4">Metric</th>
                  <th className="py-2.5 px-4 text-emerald-400 font-bold">Stage 8B Resource Optimizer</th>
                  <th className="py-2.5 px-4 text-purple-400 font-bold">Nearest Unit Baseline</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                <tr>
                  <td className="py-2.5 px-4 font-sans text-slate-400 font-semibold">Average Allocation Score</td>
                  <td className="py-2.5 px-4 text-emerald-400 font-bold">{nearestData.stage_8b_optimization?.average_score} / 100</td>
                  <td className="py-2.5 px-4 text-purple-400 font-bold">{nearestData.nearest_unit_baseline?.average_score} / 100</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 font-sans text-slate-400 font-semibold">Average Distance to Incident</td>
                  <td className="py-2.5 px-4 text-emerald-400 font-bold">{nearestData.stage_8b_optimization?.average_distance_m} m</td>
                  <td className="py-2.5 px-4 text-purple-400 font-bold">{nearestData.nearest_unit_baseline?.average_distance_m} m</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 font-sans text-slate-400 font-semibold">Capability Match Rate</td>
                  <td className="py-2.5 px-4 text-emerald-400 font-bold">{nearestData.stage_8b_optimization?.capability_match_percent}%</td>
                  <td className="py-2.5 px-4 text-purple-400 font-bold">{nearestData.nearest_unit_baseline?.capability_match_percent}%</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 font-sans text-slate-400 font-semibold">Assigned Route Health Score</td>
                  <td className="py-2.5 px-4 text-emerald-400 font-bold">{nearestData.stage_8b_optimization?.route_health_score}</td>
                  <td className="py-2.5 px-4 text-purple-400 font-bold">{nearestData.nearest_unit_baseline?.route_health_score}</td>
                </tr>
              </tbody>
            </table>
            {nearestData.interpretation_note && (
              <div className="p-3 bg-slate-900/60 border-t border-slate-800 text-xs text-slate-400 italic">
                Note: {nearestData.interpretation_note}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
