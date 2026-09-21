import React from 'react';
import { Layers } from 'lucide-react';
import type { EvaluationOverview } from '../../types/evaluation';

interface Props {
  overview: EvaluationOverview | null;
  onRunAiEval: () => void;
  loading: boolean;
}

export const AIMetricsPanel: React.FC<Props> = ({ overview, onRunAiEval, loading }) => {
  const ai = overview?.ai;
  const isEvaluated = ai?.status === 'EVALUATED';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl mb-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-emerald-400" />
          <h2 className="text-lg font-bold text-white">1. AI Road Segmentation Performance</h2>
        </div>
        <button
          onClick={onRunAiEval}
          disabled={loading}
          className="px-3 py-1.5 rounded-md bg-emerald-600/20 text-emerald-300 hover:bg-emerald-600/30 border border-emerald-500/30 text-xs font-semibold transition disabled:opacity-50"
        >
          {loading ? 'Evaluating...' : 'Run AI Evaluation'}
        </button>
      </div>

      {!isEvaluated ? (
        <div className="bg-slate-950/60 border border-dashed border-slate-800 rounded-lg p-6 text-center text-slate-400 text-sm">
          No AI evaluation data recorded. Click <span className="text-emerald-400 font-semibold">Run AI Evaluation</span> to execute accuracy benchmark on validation dataset.
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 text-center">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Dice Coefficient</div>
            <div className="text-3xl font-extrabold text-emerald-400 font-mono">{ai.dice !== null ? ai.dice : 'N/A'}</div>
            <div className="text-[11px] text-slate-500 mt-1">Spatial Overlap F1 Score</div>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 text-center">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">IoU (Jaccard Index)</div>
            <div className="text-3xl font-extrabold text-blue-400 font-mono">{ai.iou !== null ? ai.iou : 'N/A'}</div>
            <div className="text-[11px] text-slate-500 mt-1">Intersection over Union</div>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 text-center">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Precision</div>
            <div className="text-3xl font-extrabold text-purple-400 font-mono">{ai.precision !== null ? ai.precision : 'N/A'}</div>
            <div className="text-[11px] text-slate-500 mt-1">Positive Predictive Value</div>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 text-center">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Recall</div>
            <div className="text-3xl font-extrabold text-amber-400 font-mono">{ai.recall !== null ? ai.recall : 'N/A'}</div>
            <div className="text-[11px] text-slate-500 mt-1">True Positive Sensitivity</div>
          </div>
        </div>
      )}
    </div>
  );
};
