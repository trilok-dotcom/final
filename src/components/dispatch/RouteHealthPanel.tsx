import React, { useState, useEffect, useCallback } from 'react';
import type { RouteHealth, RerouteRecommendation, AlternativeRoute } from '../../types/rerouting';
import {
  evaluateRouteHealth,
  evaluateReroute,
  approveReroute,
  simulateRouteDegradation,
} from '../../services/rerouting';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Navigation,
  RefreshCw,
  Zap,
} from 'lucide-react';
import { formatDuration } from '../../lib/utils';

interface RouteHealthPanelProps {
  dispatchId: string;
  onViewAlternative?: (alternative: AlternativeRoute) => void;
  onRerouteApproved?: (newRouteId: string) => void;
}

export const RouteHealthPanel: React.FC<RouteHealthPanelProps> = ({
  dispatchId,
  onViewAlternative,
  onRerouteApproved,
}) => {
  const [loading, setLoading] = useState(false);
  const [approving, setApproving] = useState(false);
  const [healthData, setHealthData] = useState<RouteHealth | null>(null);
  const [recommendation, setRecommendation] = useState<RerouteRecommendation | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadHealthAndRecommendation = useCallback(async (scenario?: string) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const health = await evaluateRouteHealth(dispatchId, scenario);
      setHealthData(health);

      const rec = await evaluateReroute(dispatchId, scenario);
      setRecommendation(rec);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to fetch route health');
    } finally {
      setLoading(false);
    }
  }, [dispatchId]);

  useEffect(() => {
    loadHealthAndRecommendation();
  }, [loadHealthAndRecommendation]);

  const handleSimulateScenario = async (scenario: string) => {
    setSelectedScenario(scenario);
    if (!scenario) {
      await loadHealthAndRecommendation();
      return;
    }
    setLoading(true);
    setErrorMsg(null);
    try {
      const rec = await simulateRouteDegradation(dispatchId, scenario);
      setRecommendation(rec);

      const health = await evaluateRouteHealth(dispatchId, scenario);
      setHealthData(health);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!recommendation || !recommendation.recommended_route_id) return;
    setApproving(true);
    setErrorMsg(null);
    try {
      const res = await approveReroute(dispatchId, recommendation.recommended_route_id);
      if (res.success && onRerouteApproved) {
        onRerouteApproved(res.new_route_id);
      }
      // Refresh status after approval
      await loadHealthAndRecommendation();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to approve re-route');
    } finally {
      setApproving(false);
    }
  };

  if (loading && !healthData) {
    return (
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 flex flex-col items-center justify-center space-y-3 min-h-[220px]">
        <RefreshCw className="w-6 h-6 text-cyan-400 animate-spin" />
        <span className="text-slate-400 font-mono text-xs">Evaluating Route Health & AI Alternatives...</span>
      </div>
    );
  }

  const currentRoute = healthData?.current_route;
  const status = healthData?.route_health || 'HEALTHY';
  const score = healthData?.health_score ?? 100;
  const alt = recommendation?.recommended_route;

  const getStatusBadge = (st: string) => {
    switch (st) {
      case 'CRITICAL':
        return 'bg-red-500/20 text-red-400 border-red-500/40';
      case 'DEGRADED':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      case 'HEALTHY':
      default:
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';
    }
  };

  return (
    <div className="bg-slate-900/95 border border-slate-800 rounded-xl p-5 shadow-2xl space-y-5 text-slate-100 font-sans">
      {/* Header & Status */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <Activity className="w-5 h-5 text-cyan-400" />
          <h3 className="font-bold text-sm tracking-wider uppercase text-slate-200">
            Route Health Assessment
          </h3>
        </div>
        <div className="flex items-center space-x-2">
          <span
            className={`px-3 py-1 rounded-full text-xs font-mono font-bold border uppercase tracking-wider ${getStatusBadge(
              status
            )}`}
          >
            {status}
          </span>
          <button
            onClick={() => loadHealthAndRecommendation(selectedScenario)}
            disabled={loading}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Refresh Route Health"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="bg-red-950/80 border border-red-500/50 rounded-lg p-3 text-red-200 text-xs flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-4 gap-3">
        <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-3 text-center">
          <div className="text-[10px] uppercase tracking-wider text-slate-400 font-mono mb-1">
            Health Score
          </div>
          <div className="text-xl font-mono font-bold text-cyan-400">
            {score} <span className="text-xs text-slate-500 font-normal">/ 100</span>
          </div>
        </div>

        <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-3 text-center">
          <div className="text-[10px] uppercase tracking-wider text-slate-400 font-mono mb-1">
            AI Confidence
          </div>
          <div className="text-xl font-mono font-bold text-emerald-400">
            {currentRoute ? Math.round(currentRoute.confidence * 100) : 100}%
          </div>
        </div>

        <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-3 text-center">
          <div className="text-[10px] uppercase tracking-wider text-slate-400 font-mono mb-1">
            Risk Level
          </div>
          <div
            className={`text-sm font-mono font-bold uppercase ${
              currentRoute?.risk_level === 'HIGH' || currentRoute?.risk_level === 'CRITICAL'
                ? 'text-red-400'
                : currentRoute?.risk_level === 'MODERATE'
                ? 'text-amber-400'
                : 'text-emerald-400'
            }`}
          >
            {currentRoute?.risk_level || 'LOW'}
          </div>
        </div>

        <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-3 text-center">
          <div className="text-[10px] uppercase tracking-wider text-slate-400 font-mono mb-1">ETA</div>
          <div className="text-sm font-mono font-bold text-cyan-300">
            {currentRoute ? formatDuration(currentRoute.eta_seconds) : '--'}
          </div>
        </div>
      </div>

      {/* Degradation Warnings section */}
      {healthData?.degradation_detected && healthData.reasons.length > 0 && (
        <div className="bg-amber-950/30 border border-amber-500/30 rounded-lg p-3.5 space-y-2">
          <div className="flex items-center space-x-2 text-amber-400 text-xs font-bold uppercase tracking-wider">
            <AlertTriangle className="w-4 h-4" />
            <span>Degradation Detected</span>
          </div>
          <ul className="space-y-1.5 pl-5 list-disc text-xs text-amber-200/90 font-mono">
            {healthData.reasons.map((r, idx) => (
              <li key={idx}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommendation Card */}
      {recommendation?.decision === 'REROUTE_RECOMMENDED' ||
      recommendation?.decision === 'REROUTE_REQUIRED' ? (
        <div className="bg-gradient-to-br from-cyan-950/40 via-slate-950 to-slate-900 border border-cyan-500/50 rounded-xl p-4 space-y-3.5 shadow-lg relative overflow-hidden">
          <div className="absolute top-0 right-0 bg-cyan-500 text-slate-950 text-[10px] font-mono font-bold px-3 py-0.5 rounded-bl-lg uppercase tracking-wider">
            {recommendation.decision}
          </div>

          <div className="flex items-center space-x-2 text-cyan-300 font-bold text-xs uppercase tracking-wider">
            <Zap className="w-4 h-4 text-cyan-400 animate-pulse" />
            <span>AI Alternative Route Available</span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed font-sans">
            {recommendation.explanation}
          </p>

          {alt && (
            <div className="grid grid-cols-4 gap-2 bg-slate-900/80 p-3 rounded-lg border border-cyan-500/20 text-xs font-mono">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">Confidence</span>
                <span className="text-emerald-400 font-bold">
                  {Math.round(alt.confidence * 100)}%
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">Risk</span>
                <span className="text-emerald-400 font-bold">{alt.risk_level}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">ETA</span>
                <span className="text-cyan-300 font-bold">{formatDuration(alt.eta_seconds)}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">Improvement</span>
                <span className="text-cyan-400 font-bold">+{alt.health_improvement} pts</span>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center space-x-3 pt-1">
            {alt && onViewAlternative && (
              <button
                onClick={() => onViewAlternative(alt)}
                className="flex-1 px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs font-bold text-slate-200 transition-colors flex items-center justify-center space-x-1.5"
              >
                <Navigation className="w-3.5 h-3.5 text-cyan-400" />
                <span>VIEW ALTERNATIVE</span>
              </button>
            )}

            <button
              onClick={handleApprove}
              disabled={approving}
              className="flex-1 px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 rounded-lg text-xs font-mono font-bold transition-all shadow-lg flex items-center justify-center space-x-1.5 disabled:opacity-50"
            >
              {approving ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>APPLYING REROUTE...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>ACCEPT AI RE-ROUTE</span>
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3.5 text-xs text-slate-400 font-mono text-center">
          {recommendation?.explanation || 'Current route is optimal. Monitoring route health continuously.'}
        </div>
      )}

      {/* Development & Testing Simulation Controls */}
      <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono text-slate-400">
        <span className="text-[11px]">Simulate Route Event:</span>
        <select
          value={selectedScenario}
          onChange={(e) => handleSimulateScenario(e.target.value)}
          className="bg-slate-950 border border-slate-800 text-slate-300 rounded px-2.5 py-1 text-xs font-mono focus:outline-none focus:border-cyan-500"
        >
          <option value="">-- Real Production Data --</option>
          <option value="LOW_CONFIDENCE">LOW AI Confidence (0.48)</option>
          <option value="HIGH_RISK">HIGH Route Risk</option>
          <option value="ETA_INCREASE">Significant ETA Delay (+40%)</option>
          <option value="ROUTE_DISCONNECTED">Route Disconnected</option>
          <option value="UNIT_DEVIATION">Unit Deviation (&gt;150m)</option>
        </select>
      </div>
    </div>
  );
};
