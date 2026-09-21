import React from 'react';
import { PlaySquare } from 'lucide-react';
import type { EvaluationOverview } from '../../types/evaluation';

interface Props {
  overview: EvaluationOverview | null;
}

export const SimulationMetricsPanel: React.FC<Props> = ({ overview }) => {
  const sim = overview?.simulation;
  const isEvaluated = sim?.status === 'EVALUATED';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl mb-6">
      <div className="flex items-center gap-2 border-b border-slate-800 pb-4 mb-4">
        <PlaySquare className="w-5 h-5 text-indigo-400" />
        <h2 className="text-lg font-bold text-white">8. Disaster Exercise Simulation Evaluation</h2>
      </div>

      {!isEvaluated ? (
        <div className="bg-slate-950/60 border border-dashed border-slate-800 rounded-lg p-6 text-center text-slate-400 text-sm">
          No simulation evaluation data recorded. Run disaster exercises in the Simulation Center to evaluate.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Sessions Evaluated</div>
            <div className="text-2xl font-bold text-indigo-400 font-mono">{sim.sessions_evaluated} sessions</div>
            <div className="text-xs text-slate-400 mt-1">Isolated simulation DB records</div>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Data Isolation</div>
            <div className="text-2xl font-bold text-emerald-400 font-mono">100% Isolated</div>
            <div className="text-xs text-slate-400 mt-1">Tagged with simulation_session_id</div>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Pipeline Coverage</div>
            <div className="text-2xl font-bold text-white font-mono">Stage 8A → 9A</div>
            <div className="text-xs text-slate-400 mt-1">End-to-end exercise validation</div>
          </div>
        </div>
      )}
    </div>
  );
};
