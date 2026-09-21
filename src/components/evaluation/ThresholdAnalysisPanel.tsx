import React from 'react';
import { Sliders, Award } from 'lucide-react';
import type { ThresholdCurvePoint } from '../../types/evaluation';

interface Props {
  thresholdCurve: ThresholdCurvePoint[];
  bestThreshold: number | null;
  bestDice: number | null;
  productionThreshold: number;
}

export const ThresholdAnalysisPanel: React.FC<Props> = ({
  thresholdCurve,
  bestThreshold,
  bestDice,
  productionThreshold,
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl mb-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
        <div className="flex items-center gap-2">
          <Sliders className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-bold text-white">2. AI Threshold Curve Analysis</h2>
        </div>
        {bestThreshold !== null && (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-semibold">
            <Award className="w-3.5 h-3.5" />
            Optimum Threshold: <span className="font-mono">{bestThreshold}</span> (Dice: {bestDice})
          </div>
        )}
      </div>

      <p className="text-slate-400 text-xs mb-4">
        Multi-threshold validation sweep across decision probabilities. Note: Production inference remains set at{' '}
        <span className="text-emerald-400 font-mono font-bold">{productionThreshold}</span> per architectural design.
      </p>

      {thresholdCurve.length === 0 ? (
        <div className="bg-slate-950/60 border border-dashed border-slate-800 rounded-lg p-6 text-center text-slate-400 text-sm">
          Run AI Evaluation to compute threshold curve.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-950 text-xs uppercase text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-4">Threshold</th>
                <th className="py-2.5 px-4">Dice Score</th>
                <th className="py-2.5 px-4">IoU Score</th>
                <th className="py-2.5 px-4">Precision</th>
                <th className="py-2.5 px-4">Recall</th>
                <th className="py-2.5 px-4">Pixel Accuracy</th>
                <th className="py-2.5 px-4 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {thresholdCurve.map((pt) => {
                const isBest = bestThreshold !== null && Math.abs(pt.threshold - bestThreshold) < 0.01;
                const isProd = Math.abs(pt.threshold - productionThreshold) < 0.01;

                return (
                  <tr
                    key={pt.threshold}
                    className={`hover:bg-slate-800/40 transition ${
                      isBest ? 'bg-emerald-950/20 font-bold' : isProd ? 'bg-blue-950/20' : ''
                    }`}
                  >
                    <td className="py-2.5 px-4 font-bold text-white">{pt.threshold.toFixed(2)}</td>
                    <td className="py-2.5 px-4 text-emerald-400">{pt.dice.toFixed(4)}</td>
                    <td className="py-2.5 px-4 text-blue-400">{pt.iou.toFixed(4)}</td>
                    <td className="py-2.5 px-4 text-purple-400">{pt.precision.toFixed(4)}</td>
                    <td className="py-2.5 px-4 text-amber-400">{pt.recall.toFixed(4)}</td>
                    <td className="py-2.5 px-4 text-slate-300">{(pt.accuracy * 100).toFixed(2)}%</td>
                    <td className="py-2.5 px-4 text-right">
                      {isBest && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                          BEST VALIDATION
                        </span>
                      )}
                      {isProd && !isBest && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/40">
                          PRODUCTION
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
