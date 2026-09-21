import React from 'react';
import type { SimulationSummaryMetrics, SimulationSession } from '../../types/simulation';
import {
  AlertTriangle,
  Flame,
  Navigation,
  ShieldCheck,
  CheckCircle2,
  AlertOctagon,
  RefreshCw,
  Award,
} from 'lucide-react';

interface SimulationSummaryProps {
  summary: SimulationSummaryMetrics;
  session: SimulationSession;
  onFilterClick?: (type: string) => void;
}

export const SimulationSummary: React.FC<SimulationSummaryProps> = ({
  summary,
  session,
  onFilterClick,
}) => {
  const isCompleted = session.status === 'COMPLETED';

  return (
    <div className="space-y-4">
      {/* 6 Key Operational Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
        {/* Card 1: Total Incidents */}
        <div
          onClick={() => onFilterClick?.('incidents')}
          className="bg-slate-900/90 border border-slate-800 hover:border-amber-500/50 rounded-xl p-3 cursor-pointer transition shadow-md"
        >
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[10px] font-mono uppercase font-bold tracking-wider">INCIDENTS</span>
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-xl font-bold font-mono text-slate-100">{summary.incidents}</div>
          <div className="text-[10px] text-amber-400/80 font-mono mt-0.5">
            {summary.critical_incidents} CRITICAL
          </div>
        </div>

        {/* Card 2: Active Missions */}
        <div
          onClick={() => onFilterClick?.('missions')}
          className="bg-slate-900/90 border border-slate-800 hover:border-blue-500/50 rounded-xl p-3 cursor-pointer transition shadow-md"
        >
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[10px] font-mono uppercase font-bold tracking-wider">MISSIONS</span>
            <Navigation className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-xl font-bold font-mono text-slate-100">{summary.active_missions}</div>
          <div className="text-[10px] text-blue-400/80 font-mono mt-0.5">
            {summary.completed_missions} COMPLETED
          </div>
        </div>

        {/* Card 3: Fleet Resources */}
        <div
          onClick={() => onFilterClick?.('units')}
          className="bg-slate-900/90 border border-slate-800 hover:border-emerald-500/50 rounded-xl p-3 cursor-pointer transition shadow-md"
        >
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[10px] font-mono uppercase font-bold tracking-wider">DISPATCHED</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold font-mono text-slate-100">{summary.dispatched_units}</div>
          <div className="text-[10px] text-emerald-400/80 font-mono mt-0.5">
            {summary.available_units} AVAILABLE
          </div>
        </div>

        {/* Card 4: Degraded Routes */}
        <div
          onClick={() => onFilterClick?.('degraded')}
          className="bg-slate-900/90 border border-slate-800 hover:border-rose-500/50 rounded-xl p-3 cursor-pointer transition shadow-md"
        >
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[10px] font-mono uppercase font-bold tracking-wider">DEGRADED</span>
            <AlertOctagon className="w-4 h-4 text-rose-500" />
          </div>
          <div className="text-xl font-bold font-mono text-slate-100">{summary.degraded_routes}</div>
          <div className="text-[10px] text-rose-400/80 font-mono mt-0.5">HEALTH WARNINGS</div>
        </div>

        {/* Card 5: AI Reroute Recs */}
        <div
          onClick={() => onFilterClick?.('reroutes')}
          className="bg-slate-900/90 border border-slate-800 hover:border-cyan-500/50 rounded-xl p-3 cursor-pointer transition shadow-md"
        >
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[10px] font-mono uppercase font-bold tracking-wider">REROUTES</span>
            <RefreshCw className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-xl font-bold font-mono text-slate-100">
            {summary.reroute_recommendations}
          </div>
          <div className="text-[10px] text-cyan-400/80 font-mono mt-0.5">RECOMMENDED</div>
        </div>

        {/* Card 6: Open Incidents */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3 shadow-md">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[10px] font-mono uppercase font-bold tracking-wider">OPEN</span>
            <Flame className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-xl font-bold font-mono text-slate-100">{summary.open_incidents}</div>
          <div className="text-[10px] text-amber-400/80 font-mono mt-0.5">UNRESOLVED</div>
        </div>

        {/* Card 7: Completed Badge */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3 shadow-md">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[10px] font-mono uppercase font-bold tracking-wider">EXERCISE</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xs font-bold font-mono text-emerald-400 uppercase mt-1">
            {isCompleted ? 'COMPLETED' : 'IN PROGRESS'}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-0.5">STAGE 9B ENGINE</div>
        </div>
      </div>

      {/* Post-Exercise Performance Results Banner (when COMPLETED) */}
      {isCompleted && session.summary && (
        <div className="p-4 bg-gradient-to-r from-emerald-950/80 via-slate-900 to-cyan-950/80 border border-emerald-500/50 rounded-xl shadow-xl flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-emerald-500/20 border border-emerald-500/40 rounded-xl text-emerald-400">
              <Award className="w-6 h-6" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                Disaster Exercise Completed Successfully — Final Results
              </h4>
              <p className="text-xs text-slate-300 mt-0.5">
                Scenario: <span className="text-emerald-400 font-bold">{session.scenario_name}</span> •
                Duration: <span className="font-mono text-cyan-400 font-bold">03:00 mins</span> • Incidents
                Resolved: <span className="font-mono text-emerald-400 font-bold">{summary.incidents}</span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="text-center px-3 py-1.5 bg-slate-950 rounded-lg border border-slate-800">
              <div className="text-[10px] text-slate-400">AVG CONFIDENCE</div>
              <div className="text-sm font-bold text-emerald-400">
                {Math.round((session.summary.average_route_confidence || 0.82) * 100)}%
              </div>
            </div>
            <div className="text-center px-3 py-1.5 bg-slate-950 rounded-lg border border-slate-800">
              <div className="text-[10px] text-slate-400">AVG ROUTE HEALTH</div>
              <div className="text-sm font-bold text-cyan-400">
                {session.summary.average_route_health || 88.5}/100
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
