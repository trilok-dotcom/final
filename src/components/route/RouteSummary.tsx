import React from 'react';
import type { RouteResponse } from '../../types/route';
import { formatDistance, formatDuration } from '../../lib/utils';
import { Activity, Clock, Navigation, AlertTriangle, CheckCircle2 } from 'lucide-react';

interface RouteSummaryProps {
  route?: RouteResponse | null;
}

export const RouteSummary: React.FC<RouteSummaryProps> = ({ route }) => {
  return (
    <div className="w-full bg-[#0b0f19] border-t border-slate-800/80 px-4 py-2.5 flex items-center justify-between shrink-0 select-none font-mono">
      {route ? (
        /* Real Calculated Route Summary */
        <div className="flex items-center justify-between w-full text-xs">
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <span className="text-slate-400">DISTANCE:</span>
              <span className="text-slate-100 font-bold">{formatDistance(route.totalDistanceMeters)}</span>
            </div>

            <div className="flex items-center space-x-2">
              <Clock className="w-4 h-4 text-cyan-400" />
              <span className="text-slate-400">DURATION:</span>
              <span className="text-slate-100 font-bold">{formatDuration(route.estimatedDurationSeconds)}</span>
            </div>

            <div className="flex items-center space-x-2">
              <Navigation className="w-4 h-4 text-emerald-400" />
              <span className="text-slate-400">DIRECTIONS:</span>
              <span className="text-emerald-400 font-bold">{route.steps.length} MANEUVERS</span>
            </div>
          </div>

          <div className="text-[11px] text-emerald-400 bg-emerald-950/40 border border-emerald-800/50 px-2 py-0.5 rounded flex items-center space-x-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>REAL ROAD ROUTE CALCULATED</span>
          </div>
        </div>
      ) : (
        /* Empty State */
        <div className="flex items-center justify-between w-full text-xs text-slate-400">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-amber-500/80" />
              <span className="text-slate-300 font-medium">Route Summary:</span>
              <span className="text-slate-400 italic">Awaiting route calculation</span>
            </div>
          </div>

          <div className="hidden sm:flex items-center space-x-6 text-[11px]">
            <div>
              <span className="text-slate-400">DISTANCE: </span>
              <span className="text-slate-400">--</span>
            </div>
            <div>
              <span className="text-slate-400">DURATION: </span>
              <span className="text-slate-400">--</span>
            </div>
            <div>
              <span className="text-slate-400">MANEUVERS: </span>
              <span className="text-slate-400">--</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
