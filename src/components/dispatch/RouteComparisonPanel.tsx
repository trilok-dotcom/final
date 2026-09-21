import React from 'react';
import type { CurrentRouteMetrics, AlternativeRoute } from '../../types/rerouting';
import { formatDistance, formatDuration } from '../../lib/utils';
import { ArrowRightLeft, CheckCircle2, TrendingUp } from 'lucide-react';

interface RouteComparisonPanelProps {
  currentRoute: CurrentRouteMetrics;
  alternativeRoute: AlternativeRoute;
  onAcceptReroute?: () => void;
  onClose?: () => void;
  approving?: boolean;
}

export const RouteComparisonPanel: React.FC<RouteComparisonPanelProps> = ({
  currentRoute,
  alternativeRoute,
  onAcceptReroute,
  onClose,
  approving = false,
}) => {
  const currentHealth = currentRoute.health_score ?? 50;
  const altHealth = alternativeRoute.health_score;

  const etaDiff = alternativeRoute.eta_improvement_seconds;
  const confDiffPct = Math.round(alternativeRoute.confidence_improvement * 100);

  return (
    <div className="bg-slate-900 border border-cyan-500/40 rounded-xl p-5 shadow-2xl text-slate-100 font-sans space-y-5">
      {/* Title Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <ArrowRightLeft className="w-5 h-5 text-cyan-400" />
          <h3 className="font-bold text-sm tracking-wider uppercase text-slate-200">
            Route Comparison Analysis
          </h3>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-xs font-mono text-slate-400 hover:text-slate-200 px-2 py-1 rounded bg-slate-800"
          >
            CLOSE
          </button>
        )}
      </div>

      {/* Side-by-side Table Comparison */}
      <div className="grid grid-cols-2 gap-4">
        {/* CURRENT ROUTE */}
        <div className="bg-slate-950/90 border border-slate-800 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-xs font-mono font-bold uppercase text-slate-400">
              CURRENT ROUTE
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
              ACTIVE
            </span>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between">
              <span className="text-slate-400">Distance:</span>
              <span className="text-slate-200 font-bold">
                {formatDistance(currentRoute.distance_meters)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">ETA:</span>
              <span className="text-slate-200 font-bold">
                {formatDuration(currentRoute.eta_seconds)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Confidence:</span>
              <span className="text-amber-400 font-bold">
                {Math.round(currentRoute.confidence * 100)}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Risk Level:</span>
              <span
                className={`font-bold uppercase ${
                  currentRoute.risk_level === 'HIGH' || currentRoute.risk_level === 'CRITICAL'
                    ? 'text-red-400'
                    : 'text-amber-400'
                }`}
              >
                {currentRoute.risk_level}
              </span>
            </div>
            <div className="flex justify-between pt-1 border-t border-slate-800/80">
              <span className="text-slate-400">Health Score:</span>
              <span className="text-cyan-400 font-bold">{currentHealth} / 100</span>
            </div>
          </div>
        </div>

        {/* AI ALTERNATIVE ROUTE */}
        <div className="bg-cyan-950/20 border border-cyan-500/40 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-cyan-500/30 pb-2">
            <span className="text-xs font-mono font-bold uppercase text-cyan-300">
              AI ALTERNATIVE
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40">
              RECOMMENDED
            </span>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between">
              <span className="text-slate-400">Distance:</span>
              <span className="text-cyan-200 font-bold">
                {formatDistance(alternativeRoute.distance_meters)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">ETA:</span>
              <span className="text-cyan-200 font-bold">
                {formatDuration(alternativeRoute.eta_seconds)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Confidence:</span>
              <span className="text-emerald-400 font-bold">
                {Math.round(alternativeRoute.confidence * 100)}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Risk Level:</span>
              <span className="text-emerald-400 font-bold uppercase">
                {alternativeRoute.risk_level}
              </span>
            </div>
            <div className="flex justify-between pt-1 border-t border-cyan-500/20">
              <span className="text-slate-400">Health Score:</span>
              <span className="text-cyan-300 font-bold">{altHealth} / 100</span>
            </div>
          </div>
        </div>
      </div>

      {/* Key Metric Differences Box */}
      <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4 space-y-2 font-mono text-xs">
        <div className="text-[11px] font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
          <TrendingUp className="w-4 h-4 text-cyan-400" />
          <span>Quantitative Improvement Summary</span>
        </div>

        <div className="grid grid-cols-4 gap-2 text-center">
          <div className="bg-slate-900 p-2 rounded border border-slate-800">
            <span className="text-slate-400 block text-[10px]">ETA DELTA</span>
            <span className="text-emerald-400 font-bold">
              {etaDiff > 0 ? `-${etaDiff} sec` : `${etaDiff} sec`}
            </span>
          </div>

          <div className="bg-slate-900 p-2 rounded border border-slate-800">
            <span className="text-slate-400 block text-[10px]">CONFIDENCE</span>
            <span className="text-emerald-400 font-bold">
              {confDiffPct >= 0 ? `+${confDiffPct}%` : `${confDiffPct}%`}
            </span>
          </div>

          <div className="bg-slate-900 p-2 rounded border border-slate-800">
            <span className="text-slate-400 block text-[10px]">RISK CHANGE</span>
            <span className="text-cyan-300 font-bold">{alternativeRoute.risk_change}</span>
          </div>

          <div className="bg-slate-900 p-2 rounded border border-slate-800">
            <span className="text-slate-400 block text-[10px]">HEALTH DELTA</span>
            <span className="text-cyan-400 font-bold">
              {currentHealth} → {altHealth}
            </span>
          </div>
        </div>
      </div>

      {/* Action Footer */}
      {onAcceptReroute && (
        <button
          onClick={onAcceptReroute}
          disabled={approving}
          className="w-full py-3 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 rounded-xl font-mono text-xs font-bold transition-all shadow-xl flex items-center justify-center space-x-2"
        >
          <CheckCircle2 className="w-4 h-4" />
          <span>{approving ? 'APPLYING REROUTE...' : 'ACCEPT AI RE-ROUTE'}</span>
        </button>
      )}
    </div>
  );
};
