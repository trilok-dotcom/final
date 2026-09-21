import React, { useState } from 'react';
import { AlertOctagon, Check } from 'lucide-react';
import type { CommandCenterAlert } from '../../types/commandCenter';

interface CommandAlertFeedProps {
  alerts: CommandCenterAlert[];
  onAcknowledge: (alertId: string) => void;
}

export const CommandAlertFeed: React.FC<CommandAlertFeedProps> = ({ alerts, onAcknowledge }) => {
  const [filter, setFilter] = useState<'UNACK' | 'ALL'>('UNACK');

  const filteredAlerts = alerts.filter((a) => {
    if (filter === 'UNACK') return !a.acknowledged;
    return true;
  });

  const getAlertSeverityBadge = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse';
      case 'HIGH':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
      case 'MEDIUM':
        return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40';
      case 'INFO':
      default:
        return 'bg-slate-500/20 text-slate-300 border-slate-500/40';
    }
  };

  return (
    <div className="bg-slate-900/80 backdrop-blur border border-slate-800 rounded-xl p-4 flex flex-col h-full shadow-lg">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
        <div className="flex items-center gap-2">
          <AlertOctagon className="w-5 h-5 text-rose-400" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
            Central Operational Feed & Alerts
          </h2>
        </div>
        <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800">
          <button
            onClick={() => setFilter('UNACK')}
            className={`px-2 py-0.5 rounded text-[10px] font-semibold transition ${
              filter === 'UNACK' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Pending
          </button>
          <button
            onClick={() => setFilter('ALL')}
            className={`px-2 py-0.5 rounded text-[10px] font-semibold transition ${
              filter === 'ALL' ? 'bg-slate-800 text-slate-200' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All Logs
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2.5 max-h-[420px] pr-1">
        {filteredAlerts.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-xs">
            {filter === 'UNACK' ? 'All operational alerts acknowledged.' : 'No system alerts logged.'}
          </div>
        ) : (
          filteredAlerts.map((alert) => (
            <div
              key={alert.id}
              className={`p-3 rounded-lg border transition ${
                alert.acknowledged
                  ? 'bg-slate-950/40 border-slate-800/60 opacity-60'
                  : 'bg-slate-950/80 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded border text-[10px] uppercase font-semibold ${getAlertSeverityBadge(alert.severity)}`}>
                    {alert.severity}
                  </span>
                  <h4 className="text-xs font-semibold text-slate-100">{alert.title}</h4>
                </div>
                <span className="text-[10px] text-slate-500 font-mono">
                  {new Date(alert.created_at).toLocaleTimeString()}
                </span>
              </div>

              <p className="mt-1.5 text-xs text-slate-300">{alert.message}</p>

              <div className="mt-2 flex items-center justify-between pt-2 border-t border-slate-800/40 text-[10px] text-slate-400">
                <span className="font-mono text-slate-500">
                  {alert.acknowledged ? `Acked by ${alert.acknowledged_by || 'Operator'}` : 'Requires Attention'}
                </span>
                {!alert.acknowledged && (
                  <button
                    onClick={() => onAcknowledge(alert.id)}
                    className="px-2.5 py-1 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 rounded font-semibold transition flex items-center gap-1"
                  >
                    <Check className="w-3 h-3" />
                    Acknowledge
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
