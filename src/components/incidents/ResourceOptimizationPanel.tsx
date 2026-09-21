import React, { useState } from 'react';
import type { ResourceOptimizationResponse } from '../../types/resourceOptimization';
import { dispatchOptimizedPlan } from '../../services/resourceOptimization';
import {
  Layers,
  Zap,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Ambulance,
  Truck,
  Shield,
  Flame,
  Info,
  ChevronDown,
  ChevronUp,
  Cpu,
} from 'lucide-react';
import { formatDistance, formatDuration } from '../../lib/utils';

interface ResourceOptimizationPanelProps {
  optimization: ResourceOptimizationResponse;
  onDispatchConfirmed?: () => void;
  onClose?: () => void;
}

export const ResourceOptimizationPanel: React.FC<ResourceOptimizationPanelProps> = ({
  optimization,
  onDispatchConfirmed,
  onClose,
}) => {
  const [dispatching, setDispatching] = useState(false);
  const [expandedUnitId, setExpandedUnitId] = useState<string | null>(null);

  const statusUpper = optimization.resource_status.toUpperCase();
  const selectedUnits = optimization.selected_units || [];
  const candidateUnits = optimization.candidate_units || [];
  const requirements = optimization.required_resources || [];

  const handleConfirmDispatch = async () => {
    setDispatching(true);
    try {
      await dispatchOptimizedPlan(optimization.incident_id);
      if (onDispatchConfirmed) onDispatchConfirmed();
      if (onClose) onClose();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to dispatch optimized plan.');
    } finally {
      setDispatching(false);
    }
  };

  const getStatusBadge = (st: string) => {
    switch (st) {
      case 'OPTIMAL':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50';
      case 'PARTIAL':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/50';
      case 'INSUFFICIENT_RESOURCES':
      case 'NO_SUITABLE_UNITS':
        return 'bg-red-500/20 text-red-300 border-red-500/50';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const getUnitIcon = (type: string) => {
    const t = type.toUpperCase();
    if (t.includes('AMBULANCE')) return <Ambulance className="w-4 h-4 text-emerald-400" />;
    if (t.includes('FIRE')) return <Truck className="w-4 h-4 text-amber-400" />;
    if (t.includes('POLICE')) return <Shield className="w-4 h-4 text-cyan-400" />;
    return <Flame className="w-4 h-4 text-purple-400" />;
  };

  return (
    <div className="bg-[#0b0f19] border border-cyan-500/50 rounded-lg p-5 font-sans shadow-2xl space-y-4 select-none max-w-2xl w-full max-h-[85vh] overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <Cpu className="w-5 h-5 text-cyan-400 animate-pulse" />
          <h3 className="font-mono font-bold text-sm tracking-wider text-slate-100 uppercase">
            AI MULTI-UNIT RESOURCE OPTIMIZATION
          </h3>
        </div>
        <span className={`text-[10px] font-mono font-bold uppercase px-2.5 py-0.5 rounded border ${getStatusBadge(statusUpper)}`}>
          {statusUpper.replace('_', ' ')}
        </span>
      </div>

      {/* Resource Requirements Summary Grid */}
      <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800 space-y-2 font-mono text-xs">
        <span className="text-[10px] text-slate-400 font-bold uppercase block flex items-center space-x-1">
          <Layers className="w-3.5 h-3.5 text-cyan-400" />
          <span>RESOURCE REQUIREMENTS</span>
        </span>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {requirements.map((req, idx) => (
            <div key={idx} className="p-2 rounded bg-slate-950/80 border border-slate-800 space-y-0.5">
              <div className="text-[10px] text-slate-400 uppercase font-bold">{req.unit_type.replace('_', ' ')}</div>
              <div className="flex items-baseline justify-between pt-0.5">
                <span className="text-slate-300">REQ: <strong className="text-cyan-300">{req.required}</strong></span>
                <span className="text-slate-300">SEL: <strong className="text-emerald-400">{req.selected}</strong></span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* OPTIMAL RESOURCE PLAN CARDS */}
      <div className="space-y-2">
        <h4 className="font-mono font-bold text-xs text-slate-300 uppercase flex items-center space-x-1.5">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          <span>OPTIMAL RESOURCE PLAN ({selectedUnits.length} UNITS SELECTED)</span>
        </h4>

        {selectedUnits.length === 0 ? (
          <div className="p-3 rounded bg-red-950/20 border border-red-900/40 text-red-300 font-mono text-xs flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
            <span>NO SUITABLE RESCUE UNITS CURRENTLY AVAILABLE ON STANDBY.</span>
          </div>
        ) : (
          <div className="space-y-2">
            {selectedUnits.map((unit) => {
              const isExpanded = expandedUnitId === unit.rescue_unit_id;
              const fb = unit.factor_breakdown;

              return (
                <div key={unit.rescue_unit_id} className="p-3 rounded-lg bg-slate-900/90 border border-cyan-900/50 space-y-2 font-mono text-xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {getUnitIcon(unit.unit_type)}
                      <div>
                        <span className="font-bold text-cyan-300 text-sm">{unit.unit_code}</span>
                        <span className="text-[10px] text-slate-400 ml-2 uppercase">({unit.unit_type.replace('_', ' ')})</span>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold text-emerald-400 bg-emerald-950/60 border border-emerald-800 px-2 py-0.5 rounded">
                        SCORE {unit.optimization_score.toFixed(1)}
                      </span>
                      <button
                        type="button"
                        onClick={() => setExpandedUnitId(isExpanded ? null : unit.rescue_unit_id)}
                        className="text-slate-400 hover:text-cyan-300 transition-colors"
                      >
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  {/* Quick Metrics */}
                  <div className="grid grid-cols-4 gap-1.5 text-[10px] pt-1 border-t border-slate-800/80">
                    <div>ETA: <strong className="text-cyan-300">{formatDuration(unit.estimated_duration_seconds)}</strong></div>
                    <div>DIST: <strong className="text-slate-200">{formatDistance(unit.distance_meters)}</strong></div>
                    <div>CONF: <strong className="text-emerald-400">{(unit.average_confidence * 100).toFixed(1)}%</strong></div>
                    <div>RISK: <strong className="text-emerald-400 uppercase">{unit.risk_level}</strong></div>
                  </div>

                  {/* "WHY THIS UNIT?" Explainability Breakdown */}
                  {isExpanded && (
                    <div className="p-2.5 rounded bg-slate-950/90 border border-slate-800 space-y-2 text-[10px] pt-2">
                      <div className="text-cyan-300 font-bold flex items-center space-x-1">
                        <Info className="w-3 h-3 text-cyan-400" />
                        <span>WHY THIS UNIT WAS SELECTED:</span>
                      </div>
                      <p className="text-slate-300 leading-relaxed font-sans">{unit.selection_reason}</p>

                      <div className="grid grid-cols-3 gap-1.5 pt-1">
                        <div className="p-1 rounded bg-slate-900 border border-slate-800">ETA SCORE: <strong>{fb.eta_score}</strong></div>
                        <div className="p-1 rounded bg-slate-900 border border-slate-800">ROUTE SAFETY: <strong>{fb.route_safety_score}</strong></div>
                        <div className="p-1 rounded bg-slate-900 border border-slate-800">CONFIDENCE: <strong>{fb.ai_confidence_score}</strong></div>
                        <div className="p-1 rounded bg-slate-900 border border-slate-800">CAPABILITY: <strong>{fb.capability_score}</strong></div>
                        <div className="p-1 rounded bg-slate-900 border border-slate-800">AVAILABILITY: <strong>{fb.availability_score}</strong></div>
                        <div className="p-1 rounded bg-slate-900 border border-slate-800">OPERATIONAL: <strong>{fb.operational_score}</strong></div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Candidate Comparison Table */}
      {candidateUnits.length > 0 && (
        <div className="space-y-1.5">
          <h4 className="font-mono font-bold text-xs text-slate-300 uppercase flex items-center space-x-1.5">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span>CANDIDATE COMPARISON ({candidateUnits.length} EVALUATED)</span>
          </h4>
          <div className="overflow-x-auto rounded border border-slate-800 bg-slate-950 font-mono text-[10px]">
            <table className="w-full text-left">
              <thead className="bg-slate-900 text-slate-400 border-b border-slate-800 uppercase">
                <tr>
                  <th className="p-2">UNIT</th>
                  <th className="p-2">TYPE</th>
                  <th className="p-2">SCORE</th>
                  <th className="p-2">ETA</th>
                  <th className="p-2">CONF</th>
                  <th className="p-2">RISK</th>
                  <th className="p-2">STATUS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {candidateUnits.map((cand) => (
                  <tr key={cand.rescue_unit_id} className={cand.is_selected ? 'bg-cyan-950/20 text-slate-200 font-bold' : 'text-slate-400'}>
                    <td className="p-2 text-cyan-300">{cand.unit_code}</td>
                    <td className="p-2 uppercase">{cand.unit_type.replace('_', ' ')}</td>
                    <td className="p-2 text-cyan-300 font-bold">{cand.optimization_score.toFixed(1)}</td>
                    <td className="p-2">{formatDuration(cand.estimated_duration_seconds)}</td>
                    <td className="p-2 text-emerald-400">{(cand.average_confidence * 100).toFixed(0)}%</td>
                    <td className="p-2 uppercase">{cand.risk_level}</td>
                    <td className="p-2">
                      {cand.is_selected ? (
                        <span className="px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 uppercase font-bold">
                          SELECTED
                        </span>
                      ) : (
                        <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 uppercase">
                          ALTERNATIVE
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Operator Confirm Dispatch Button */}
      {selectedUnits.length > 0 && (
        <div className="pt-2">
          <button
            type="button"
            disabled={dispatching}
            onClick={handleConfirmDispatch}
            className="w-full py-2.5 px-4 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-mono font-bold text-xs rounded uppercase flex items-center justify-center space-x-2 shadow-xl cursor-pointer transition-colors"
          >
            {dispatching ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-slate-950" />
                <span>DISPATCHING MULTI-UNIT MISSION...</span>
              </>
            ) : (
              <>
                <Zap className="w-4 h-4 fill-current" />
                <span>DISPATCH OPTIMIZED PLAN ({selectedUnits.length} UNITS)</span>
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};
