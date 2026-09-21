import React, { useState, useEffect } from 'react';
import { AlertCircle, AlertTriangle, Info, CheckCircle2, Brain } from 'lucide-react';
import { getIncidents } from '../../services/incidents';

interface IncidentStatsProps {
  stats?: {
    critical: number;
    high: number;
    moderate: number;
    resolved: number;
  };
}

export const IncidentStats: React.FC<IncidentStatsProps> = ({ stats: propStats }) => {
  const [liveStats, setLiveStats] = useState<{
    critical: number;
    high: number;
    moderate: number;
    resolved: number;
  }>({ critical: 2, high: 1, moderate: 0, resolved: 0 });

  useEffect(() => {
    if (propStats) {
      return;
    }

    const fetchStats = async () => {
      try {
        const incidents = await getIncidents();
        if (incidents.length > 0) {
          let critical = 0;
          let high = 0;
          let moderate = 0;
          let resolved = 0;

          incidents.forEach((inc) => {
            const sev = (inc.severity || 'low').toString().toUpperCase();
            const st = (inc.status || 'REPORTED').toString().toUpperCase();

            if (st === 'RESOLVED') {
              resolved++;
            } else if (sev === 'CRITICAL') {
              critical++;
            } else if (sev === 'HIGH') {
              high++;
            } else {
              moderate++;
            }
          });

          setLiveStats({ critical, high, moderate, resolved });
        }
      } catch {
        // Fallback
      }
    };

    fetchStats();
  }, [propStats]);

  const stats = propStats || liveStats;

  return (
    <div className="bg-[#0b0f19] border border-slate-800 rounded-lg p-3 font-mono select-none shadow-xl">
      <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800 text-xs">
        <span className="font-bold text-slate-200 tracking-wider flex items-center space-x-1.5">
          <Brain className="w-3.5 h-3.5 text-cyan-400" />
          <span>ACTIVE EMERGENCY TRIAGE</span>
        </span>
        <span className="text-[10px] text-cyan-400 font-bold">AI ENGINE RUNNING</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
        {/* Critical */}
        <div className="p-2 rounded bg-red-950/30 border border-red-900/40 flex items-center justify-between">
          <div className="flex items-center space-x-1.5 text-red-400">
            <AlertCircle className="w-3.5 h-3.5" />
            <span className="text-[11px] font-semibold">Critical</span>
          </div>
          <span className="font-bold text-sm text-red-300">{stats.critical}</span>
        </div>

        {/* High */}
        <div className="p-2 rounded bg-orange-950/30 border border-orange-900/40 flex items-center justify-between">
          <div className="flex items-center space-x-1.5 text-orange-400">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span className="text-[11px] font-semibold">High</span>
          </div>
          <span className="font-bold text-sm text-orange-300">{stats.high}</span>
        </div>

        {/* Moderate */}
        <div className="p-2 rounded bg-amber-950/20 border border-amber-900/30 flex items-center justify-between">
          <div className="flex items-center space-x-1.5 text-amber-400">
            <Info className="w-3.5 h-3.5" />
            <span className="text-[11px] font-semibold">Moderate</span>
          </div>
          <span className="font-bold text-sm text-amber-300">{stats.moderate}</span>
        </div>

        {/* Resolved */}
        <div className="p-2 rounded bg-emerald-950/20 border border-emerald-900/30 flex items-center justify-between">
          <div className="flex items-center space-x-1.5 text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span className="text-[11px] font-semibold">Resolved</span>
          </div>
          <span className="font-bold text-sm text-emerald-300">{stats.resolved}</span>
        </div>
      </div>
    </div>
  );
};
