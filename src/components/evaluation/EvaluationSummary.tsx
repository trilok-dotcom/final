import React from 'react';
import { Play, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import type { EvaluationOverview } from '../../types/evaluation';

interface Props {
  overview: EvaluationOverview | null;
  loading: boolean;
  onRunAll: () => void;
  onRefresh: () => void;
}

export const EvaluationSummary: React.FC<Props> = ({ overview, loading, onRunAll, onRefresh }) => {
  const modelVer = overview?.system_info?.model_version || 'U-Net + ResNet-34 V2';
  const datasetVer = overview?.system_info?.dataset_version || 'SpaceNet 5 AOI 8 Mumbai';
  const threshold = overview?.system_info?.production_threshold ?? 0.25;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl mb-6">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-6 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold text-white tracking-tight">System Evaluation & Analytics</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              STAGE 10
            </span>
          </div>
          <p className="text-slate-400 text-sm">
            Empirical accuracy benchmarks, threshold sweeps, latency stats, routing metrics & neutral baseline comparisons
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onRefresh}
            disabled={loading}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 text-sm font-medium transition disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh Overview
          </button>
          <button
            onClick={onRunAll}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-500 text-sm font-semibold shadow-lg shadow-emerald-950/50 transition disabled:opacity-50"
          >
            <Play className="w-4 h-4 fill-white" />
            Run Full Evaluation Chain
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-4">
          <span className="text-xs uppercase tracking-wider text-slate-500 font-semibold block mb-1">Model Engine</span>
          <div className="text-lg font-bold text-slate-100">{modelVer}</div>
          <div className="text-xs text-slate-400 mt-1 flex items-center gap-1">
            <span>Production Threshold:</span>
            <span className="font-mono text-emerald-400 font-bold">{threshold}</span>
          </div>
        </div>

        <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-4">
          <span className="text-xs uppercase tracking-wider text-slate-500 font-semibold block mb-1">Evaluation Dataset</span>
          <div className="text-lg font-bold text-slate-100">{datasetVer}</div>
          <div className="text-xs text-slate-400 mt-1">204 Validation Tiles (1300x1300 SpaceNet 5)</div>
        </div>

        <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-4">
          <span className="text-xs uppercase tracking-wider text-slate-500 font-semibold block mb-1">System State</span>
          <div className="flex items-center gap-2 mt-0.5">
            {overview?.ai.status === 'EVALUATED' ? (
              <>
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <span className="text-base font-semibold text-emerald-400">Evaluation Complete</span>
              </>
            ) : (
              <>
                <AlertCircle className="w-5 h-5 text-amber-400" />
                <span className="text-base font-semibold text-amber-400">Pending Evaluation Run</span>
              </>
            )}
          </div>
          <div className="text-xs text-slate-400 mt-1">
            {overview?.generated_at ? `Last run: ${new Date(overview.generated_at).toLocaleString()}` : 'No evaluation recorded'}
          </div>
        </div>
      </div>
    </div>
  );
};
