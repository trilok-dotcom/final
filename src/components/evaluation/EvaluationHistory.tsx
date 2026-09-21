import React from 'react';
import { History, Download, FileText } from 'lucide-react';
import type { EvaluationRun } from '../../types/evaluation';
import { evaluationService } from '../../services/evaluation';

interface Props {
  runs: EvaluationRun[];
  onRefresh: () => void;
}

export const EvaluationHistory: React.FC<Props> = ({ runs }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-slate-400" />
          <h2 className="text-lg font-bold text-white">10. Historical Evaluation Runs & Data Export</h2>
        </div>
        <span className="text-xs text-slate-400 font-mono">{runs.length} Runs Recorded</span>
      </div>

      {runs.length === 0 ? (
        <div className="bg-slate-950/60 border border-dashed border-slate-800 rounded-lg p-6 text-center text-slate-400 text-sm">
          No evaluation run history recorded yet.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-950 text-xs uppercase text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-4">Run ID</th>
                <th className="py-2.5 px-4">Evaluation Type</th>
                <th className="py-2.5 px-4">Model & Dataset</th>
                <th className="py-2.5 px-4">Samples</th>
                <th className="py-2.5 px-4">Timestamp</th>
                <th className="py-2.5 px-4">Status</th>
                <th className="py-2.5 px-4 text-right">Export Data</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {runs.map((r) => (
                <tr key={r.id} className="hover:bg-slate-800/40 transition">
                  <td className="py-2.5 px-4 font-bold text-white text-xs">{r.id}</td>
                  <td className="py-2.5 px-4">
                    <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-slate-800 text-slate-200 border border-slate-700">
                      {r.evaluation_type}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-xs font-sans text-slate-400">
                    {r.model_version || 'U-Net ResNet-34 V2'} ({r.dataset_version || 'SpaceNet 5'})
                  </td>
                  <td className="py-2.5 px-4 text-slate-300">{r.sample_count}</td>
                  <td className="py-2.5 px-4 text-xs text-slate-400 font-sans">
                    {new Date(r.started_at).toLocaleString()}
                  </td>
                  <td className="py-2.5 px-4">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                        r.status === 'COMPLETED'
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : r.status === 'FAILED'
                          ? 'bg-red-500/10 text-red-400 border-red-500/20'
                          : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      }`}
                    >
                      {r.status}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <a
                        href={evaluationService.getExportUrl(r.id, 'json')}
                        download={`evaluation_${r.id}.json`}
                        className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition"
                        title="Export JSON"
                      >
                        <FileText className="w-3.5 h-3.5" />
                      </a>
                      <a
                        href={evaluationService.getExportUrl(r.id, 'csv')}
                        download={`evaluation_${r.id}.csv`}
                        className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition"
                        title="Export CSV"
                      >
                        <Download className="w-3.5 h-3.5 text-emerald-400" />
                      </a>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
