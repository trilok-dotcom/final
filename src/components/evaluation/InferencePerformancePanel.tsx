import React from 'react';
import { Zap, Cpu } from 'lucide-react';
import type { InferenceLatencyStats } from '../../types/evaluation';

interface Props {
  latencyStats: InferenceLatencyStats | null;
}

export const InferencePerformancePanel: React.FC<Props> = ({ latencyStats }) => {
  if (!latencyStats) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl mb-6">
        <div className="flex items-center gap-2 border-b border-slate-800 pb-4 mb-4">
          <Zap className="w-5 h-5 text-amber-400" />
          <h2 className="text-lg font-bold text-white">3. Inference Latency & Pipeline Timing</h2>
        </div>
        <div className="bg-slate-950/60 border border-dashed border-slate-800 rounded-lg p-6 text-center text-slate-400 text-sm">
          Run AI Evaluation to benchmark inference timing statistics.
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl mb-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-amber-400" />
          <h2 className="text-lg font-bold text-white">3. Inference Latency & Pipeline Timing</h2>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-950 px-3 py-1 rounded-full border border-slate-800">
          <Cpu className="w-3.5 h-3.5 text-amber-400" />
          Device: <span className="font-mono text-white font-semibold">{latencyStats.device}</span> ({latencyStats.sample_count} sample runs)
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
        <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-center">
          <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold block">Preprocessing</span>
          <div className="text-xl font-bold text-slate-200 font-mono mt-1">{latencyStats.preprocess_mean_ms} ms</div>
          <span className="text-[10px] text-slate-500">Image resize & normalization</span>
        </div>

        <div className="bg-slate-950 border border-amber-500/30 bg-amber-500/5 rounded-lg p-3 text-center">
          <span className="text-xs text-amber-400 uppercase tracking-wider font-semibold block">Model Inference (Mean)</span>
          <div className="text-xl font-bold text-amber-400 font-mono mt-1">{latencyStats.inference_mean_ms} ms</div>
          <span className="text-[10px] text-slate-400">Pure GPU/CPU forward pass</span>
        </div>

        <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-center">
          <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold block">Postprocessing</span>
          <div className="text-xl font-bold text-slate-200 font-mono mt-1">{latencyStats.postprocess_mean_ms} ms</div>
          <span className="text-[10px] text-slate-500">Binarization & graph extraction</span>
        </div>

        <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-center">
          <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold block">Total Pipeline (Mean)</span>
          <div className="text-xl font-bold text-emerald-400 font-mono mt-1">{latencyStats.total_pipeline_mean_ms} ms</div>
          <span className="text-[10px] text-slate-500">End-to-end request latency</span>
        </div>
      </div>

      <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Inference Distribution Breakdown (ms)</div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-center font-mono text-sm">
          <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Mean</span>
            <span className="text-slate-200 font-bold">{latencyStats.inference_mean_ms}</span>
          </div>
          <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Median</span>
            <span className="text-slate-200 font-bold">{latencyStats.inference_median_ms}</span>
          </div>
          <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Min</span>
            <span className="text-emerald-400 font-bold">{latencyStats.inference_min_ms}</span>
          </div>
          <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Max</span>
            <span className="text-amber-400 font-bold">{latencyStats.inference_max_ms}</span>
          </div>
          <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Std Dev</span>
            <span className="text-purple-400 font-bold">{latencyStats.inference_std_ms}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
