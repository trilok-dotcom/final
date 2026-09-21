import React from 'react';
import { AlertTriangle, Shield, Navigation, AlertOctagon } from 'lucide-react';
import type { CommandCenterSummary } from '../../types/commandCenter';

interface CommandSummaryCardsProps {
  summary: CommandCenterSummary;
  onFilterClick?: (filterType: string) => void;
}

export const CommandSummaryCards: React.FC<CommandSummaryCardsProps> = ({ summary, onFilterClick }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* 1. Incident Command Summary */}
      <div 
        onClick={() => onFilterClick && onFilterClick('incidents')}
        className="bg-slate-900/80 backdrop-blur border border-slate-800 rounded-xl p-4 shadow-lg hover:border-amber-500/50 transition cursor-pointer group"
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-amber-400">Incident Command</span>
          <div className="p-2 bg-amber-500/10 rounded-lg text-amber-400 group-hover:scale-110 transition">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-3xl font-bold text-white">{summary.open_incidents}</span>
          <span className="text-xs text-slate-400">/ {summary.total_incidents} total</span>
        </div>
        <div className="mt-2 flex items-center gap-3 text-xs text-slate-400">
          <span className="flex items-center gap-1 text-red-400 font-medium">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
            {summary.critical_incidents} Critical
          </span>
          <span className="text-amber-400 font-medium">{summary.high_incidents} High</span>
        </div>
      </div>

      {/* 2. Fleet Availability */}
      <div 
        onClick={() => onFilterClick && onFilterClick('fleet')}
        className="bg-slate-900/80 backdrop-blur border border-slate-800 rounded-xl p-4 shadow-lg hover:border-emerald-500/50 transition cursor-pointer group"
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">Fleet Status</span>
          <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-400 group-hover:scale-110 transition">
            <Shield className="w-5 h-5" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-3xl font-bold text-white">{summary.available_units}</span>
          <span className="text-xs text-slate-400">/ {summary.total_units} units ready</span>
        </div>
        <div className="mt-2 flex items-center gap-3 text-xs text-slate-400">
          <span className="text-emerald-400 font-medium">{summary.available_units} Available</span>
          <span className="text-blue-400 font-medium">{summary.busy_units} Deployed</span>
        </div>
      </div>

      {/* 3. Live Mission Tracking */}
      <div 
        onClick={() => onFilterClick && onFilterClick('missions')}
        className="bg-slate-900/80 backdrop-blur border border-slate-800 rounded-xl p-4 shadow-lg hover:border-blue-500/50 transition cursor-pointer group"
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-blue-400">Active Telemetry</span>
          <div className="p-2 bg-blue-500/10 rounded-lg text-blue-400 group-hover:scale-110 transition">
            <Navigation className="w-5 h-5" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-3xl font-bold text-white">{summary.active_missions}</span>
          <span className="text-xs text-slate-400">en route / on scene</span>
        </div>
        <div className="mt-2 flex items-center gap-3 text-xs text-slate-400">
          <span className="text-sky-400 font-medium">{summary.pending_dispatches} Pending Dispatch</span>
        </div>
      </div>

      {/* 4. Route Health & Alerts */}
      <div 
        onClick={() => onFilterClick && onFilterClick('alerts')}
        className={`bg-slate-900/80 backdrop-blur border rounded-xl p-4 shadow-lg transition cursor-pointer group ${
          summary.degraded_routes > 0 || summary.unacknowledged_alerts > 0
            ? 'border-rose-500/60 bg-rose-950/20 hover:border-rose-500'
            : 'border-slate-800 hover:border-purple-500/50'
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-rose-400">Route Integrity</span>
          <div className="p-2 bg-rose-500/10 rounded-lg text-rose-400 group-hover:scale-110 transition">
            <AlertOctagon className="w-5 h-5" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-3xl font-bold text-white">{summary.degraded_routes}</span>
          <span className="text-xs text-slate-400">degraded routes</span>
        </div>
        <div className="mt-2 flex items-center gap-3 text-xs text-slate-400">
          <span className="text-rose-400 font-medium">{summary.unacknowledged_alerts} Alerts Pending</span>
        </div>
      </div>
    </div>
  );
};
