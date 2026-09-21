import React from 'react';
import type { IncidentIntelligence } from '../../types/intelligence';
import {
  Brain,
  Flame,
  Ambulance,
  Truck,
  Shield,
  Activity,
  Layers,
  Sparkles,
} from 'lucide-react';

interface IncidentIntelligencePanelProps {
  intelligence: IncidentIntelligence;
  onClose?: () => void;
}

export const IncidentIntelligencePanel: React.FC<IncidentIntelligencePanelProps> = ({
  intelligence,
}) => {
  const score = intelligence.priority_score;
  const prioUpper = intelligence.priority.toUpperCase();
  const riskUpper = intelligence.risk_level.toUpperCase();
  const urgUpper = intelligence.urgency.toUpperCase();

  const getPriorityBadge = (prio: string) => {
    switch (prio) {
      case 'CRITICAL':
        return 'bg-red-500/20 text-red-300 border-red-500/50 shadow-red-500/20';
      case 'HIGH':
        return 'bg-orange-500/20 text-orange-300 border-orange-500/50 shadow-orange-500/20';
      case 'MEDIUM':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/50';
      case 'LOW':
      default:
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50';
    }
  };

  const getResourceIcon = (type: string) => {
    const t = type.toUpperCase();
    if (t.includes('AMBULANCE')) return <Ambulance className="w-4 h-4 text-emerald-400" />;
    if (t.includes('FIRE')) return <Truck className="w-4 h-4 text-amber-400" />;
    if (t.includes('POLICE')) return <Shield className="w-4 h-4 text-cyan-400" />;
    return <Flame className="w-4 h-4 text-purple-400" />;
  };

  return (
    <div className="bg-[#0b0f19] border border-cyan-500/50 rounded-lg p-5 font-sans shadow-2xl space-y-4 select-none max-w-xl w-full">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <Brain className="w-5 h-5 text-cyan-400 animate-pulse" />
          <h3 className="font-mono font-bold text-sm tracking-wider text-slate-100 uppercase">
            AI INCIDENT INTELLIGENCE ANALYSIS
          </h3>
        </div>
        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700">
          {intelligence.incident_code || intelligence.incident_id}
        </span>
      </div>

      {/* Score Meter & Badges Grid */}
      <div className="p-3.5 rounded-lg bg-slate-900/90 border border-slate-800 space-y-3 font-mono">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <span className="text-xs text-slate-300 font-bold uppercase">PRIORITY SCORE</span>
          </div>
          <div className="flex items-baseline space-x-1">
            <span className="text-2xl font-bold text-cyan-300">{score.toFixed(1)}</span>
            <span className="text-xs text-slate-500">/ 100</span>
          </div>
        </div>

        {/* Score Progress Bar */}
        <div className="w-full h-2.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800 relative">
          <div
            className="h-full bg-gradient-to-r from-emerald-500 via-amber-500 via-orange-500 to-red-500 transition-all duration-700"
            style={{ width: `${Math.max(5, score)}%` }}
          />
        </div>

        {/* Badges */}
        <div className="grid grid-cols-3 gap-2 pt-1">
          <div className="p-2 rounded bg-slate-950/80 border border-slate-800 text-center">
            <span className="text-[9px] text-slate-400 uppercase block">PRIORITY</span>
            <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded border mt-0.5 inline-block ${getPriorityBadge(prioUpper)}`}>
              {prioUpper}
            </span>
          </div>

          <div className="p-2 rounded bg-slate-950/80 border border-slate-800 text-center">
            <span className="text-[9px] text-slate-400 uppercase block">RISK LEVEL</span>
            <span className="text-[10px] font-bold text-amber-300 uppercase px-1.5 py-0.5 rounded bg-amber-950/50 border border-amber-800 mt-0.5 inline-block">
              {riskUpper}
            </span>
          </div>

          <div className="p-2 rounded bg-slate-950/80 border border-slate-800 text-center">
            <span className="text-[9px] text-slate-400 uppercase block">URGENCY</span>
            <span className="text-[10px] font-bold text-cyan-300 uppercase px-1.5 py-0.5 rounded bg-cyan-950/50 border border-cyan-800 mt-0.5 inline-block">
              {urgUpper}
            </span>
          </div>
        </div>
      </div>

      {/* Recommended Deployment Resources */}
      <div className="space-y-2">
        <h4 className="font-mono font-bold text-xs text-slate-300 uppercase flex items-center space-x-1.5">
          <Layers className="w-3.5 h-3.5 text-cyan-400" />
          <span>RECOMMENDED RESPONSE RESOURCES</span>
        </h4>
        <div className="space-y-1.5 font-mono text-xs">
          {intelligence.recommended_resources.map((res, idx) => (
            <div key={idx} className="p-2 rounded bg-slate-900/80 border border-slate-800/90 flex items-start justify-between gap-2">
              <div className="flex items-center space-x-2">
                {getResourceIcon(res.unit_type)}
                <div>
                  <div className="font-bold text-slate-200 uppercase">
                    {res.unit_type.replace('_', ' ')} <span className="text-cyan-400">×{res.quantity}</span>
                  </div>
                  <div className="text-[10px] text-slate-400">{res.reason}</div>
                </div>
              </div>
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 uppercase font-bold shrink-0">
                NEEDED
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* AI Explanation Summary */}
      <div className="p-3 rounded bg-cyan-950/20 border border-cyan-900/40 space-y-1 font-mono text-xs">
        <span className="text-[10px] text-cyan-400 font-bold uppercase block flex items-center space-x-1">
          <Activity className="w-3 h-3" />
          <span>AI REASONING SUMMARY</span>
        </span>
        <p className="text-slate-300 leading-relaxed text-[11px] font-sans">
          {intelligence.explanation}
        </p>
      </div>

      {/* 5-Factor Contributing Factors Breakdown */}
      <div className="space-y-2">
        <h4 className="font-mono font-bold text-xs text-slate-300 uppercase flex items-center space-x-1.5">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          <span>CONTRIBUTING FACTORS BREAKDOWN</span>
        </h4>
        <div className="space-y-2 font-mono text-xs">
          {intelligence.factors.map((factor, idx) => (
            <div key={idx} className="space-y-1 bg-slate-900/50 p-2 rounded border border-slate-800/80">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-slate-300 font-bold">{factor.name}</span>
                <span className="text-cyan-300 font-bold">
                  +{factor.weighted_score.toFixed(1)} <span className="text-slate-500 text-[10px]">({(factor.weight * 100).toFixed(0)}%)</span>
                </span>
              </div>
              <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                <div
                  className="h-full bg-cyan-500"
                  style={{ width: `${Math.max(4, factor.raw_score)}%` }}
                />
              </div>
              <div className="text-[10px] text-slate-400 truncate">{factor.reason}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
