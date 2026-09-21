import React from 'react';
import type { RouteResponse, AIRouteResponse } from '../../types/route';
import {
  Navigation,
  MapPin,
  AlertCircle,
  CornerDownRight,
  CornerDownLeft,
  ArrowUp,
  Flag,
  RotateCcw,
  Cpu,
  Zap,
} from 'lucide-react';
import { formatDistance, formatDuration } from '../../lib/utils';

interface DirectionsPanelProps {
  route?: RouteResponse | null;
  aiRoute?: AIRouteResponse | null;
  routingMode?: 'standard' | 'ai';
  selectedVehicle?: string;
}

export const DirectionsPanel: React.FC<DirectionsPanelProps> = ({
  route,
  aiRoute,
  routingMode = 'standard',
  selectedVehicle = 'ambulance',
}) => {
  const getTurnIcon = (turnType: string) => {
    switch (turnType) {
      case 'left':
      case 'slight_left':
        return <CornerDownLeft className="w-3.5 h-3.5 text-cyan-400" />;
      case 'right':
      case 'slight_right':
        return <CornerDownRight className="w-3.5 h-3.5 text-cyan-400" />;
      case 'u_turn':
        return <RotateCcw className="w-3.5 h-3.5 text-amber-400" />;
      case 'arrive':
        return <Flag className="w-3.5 h-3.5 text-emerald-400" />;
      case 'start':
        return <Zap className="w-3.5 h-3.5 text-cyan-400" />;
      default:
        return <ArrowUp className="w-3.5 h-3.5 text-slate-300" />;
    }
  };

  const isAiActive = routingMode === 'ai' && Boolean(aiRoute);

  return (
    <div className="w-full h-full bg-[#0b0f19] border-l border-slate-800/80 flex flex-col justify-between overflow-y-auto select-none p-4 font-sans">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            {isAiActive ? (
              <Cpu className="w-4 h-4 text-cyan-400 animate-pulse" />
            ) : (
              <Navigation className="w-4 h-4 text-cyan-400" />
            )}
            <h3 className="font-mono font-bold text-sm tracking-wider text-slate-100 uppercase">
              {isAiActive ? 'AI EMERGENCY ROUTE' : 'TURN-BY-TURN DIRECTIONS'}
            </h3>
          </div>
          <span
            className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
              isAiActive
                ? 'bg-cyan-950/80 text-cyan-300 border-cyan-500/40'
                : 'bg-slate-900 text-slate-400 border-slate-800'
            }`}
          >
            {isAiActive
              ? 'AI U-NET + DIJKSTRA'
              : route
              ? `${route.steps.length} STEPS`
              : 'OSRM NAV'}
          </span>
        </div>

        {/* AI EMERGENCY ROUTE DISPLAY */}
        {isAiActive && aiRoute ? (
          <div className="mt-4 space-y-4">
            {/* AI Summary Box */}
            <div className="p-3 rounded bg-cyan-950/30 border border-cyan-900/50 space-y-2.5 font-mono">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400 uppercase">STATUS:</span>
                <span className="text-emerald-400 font-bold uppercase tracking-wider">
                  {aiRoute.status}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400 uppercase">TOTAL DISTANCE:</span>
                <span className="text-cyan-300 font-bold">
                  {formatDistance(aiRoute.total_distance_meters)}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400 uppercase">ESTIMATED TIME:</span>
                <span className="text-cyan-300 font-bold">
                  {formatDuration(aiRoute.estimated_duration_seconds)}
                </span>
              </div>

              {/* AI Confidence & Risk */}
              <div className="pt-2 border-t border-cyan-900/40 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400 uppercase">AI ROAD CONFIDENCE:</span>
                  <span className="text-emerald-400 font-bold">
                    {(aiRoute.average_confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400 uppercase">AI CONFIDENCE RISK:</span>
                  <span
                    className={`font-bold uppercase px-1.5 py-0.5 rounded text-[10px] ${
                      aiRoute.risk_level === 'low'
                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        : aiRoute.risk_level === 'moderate'
                        ? 'bg-amber-950 text-amber-300 border border-amber-800'
                        : 'bg-red-950 text-red-300 border border-red-800'
                    }`}
                  >
                    {aiRoute.risk_level}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400 uppercase">VEHICLE TYPE:</span>
                  <span className="text-slate-200 font-bold uppercase">
                    {selectedVehicle.replace('_', ' ')}
                  </span>
                </div>
              </div>

              {/* Snapping offset notifications if snapping occurred */}
              {(aiRoute.snapped_start.distance_to_road_meters > 0.5 ||
                aiRoute.snapped_destination.distance_to_road_meters > 0.5) && (
                <div className="pt-2 border-t border-cyan-900/40 text-[11px] text-cyan-300/80 space-y-1">
                  {aiRoute.snapped_start.distance_to_road_meters > 0.5 && (
                    <div>
                      Start snapped to nearest road ({aiRoute.snapped_start.distance_to_road_meters}m offset)
                    </div>
                  )}
                  {aiRoute.snapped_destination.distance_to_road_meters > 0.5 && (
                    <div>
                      Destination snapped ({aiRoute.snapped_destination.distance_to_road_meters}m offset)
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Turn-by-Turn Steps */}
            <div className="space-y-2">
              <span className="text-xs font-mono text-slate-400 uppercase block">
                AI ROUTE STEPS ({aiRoute.steps.length})
              </span>
              {aiRoute.steps.map((step, idx) => (
                <div
                  key={step.id || idx}
                  className="p-3 rounded bg-slate-900/70 border border-slate-800 hover:border-cyan-900 flex items-start space-x-3 text-xs transition-colors"
                >
                  <div className="w-6 h-6 rounded bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0 mt-0.5">
                    {getTurnIcon(step.turn_type)}
                  </div>
                  <div className="w-full">
                    <div className="font-semibold text-slate-100 leading-snug">
                      {step.instruction}
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono mt-1 pt-1 border-t border-slate-800/40">
                      <span>{step.road_name}</span>
                      <span className="text-cyan-400 font-bold">
                        {step.distance_meters > 0
                          ? formatDistance(step.distance_meters)
                          : formatDuration(step.duration_seconds)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : route ? (
          /* Standard OSRM Route Display */
          <div className="mt-4 space-y-4">
            <div className="p-3 rounded bg-slate-900 border border-slate-800 space-y-2 font-mono">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">TOTAL ROUTE DISTANCE:</span>
                <span className="text-slate-100 font-bold">
                  {formatDistance(route.totalDistanceMeters)}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">ESTIMATED DRIVE TIME:</span>
                <span className="text-slate-100 font-bold">
                  {formatDuration(route.estimatedDurationSeconds)}
                </span>
              </div>
            </div>

            <div className="space-y-2">
              <span className="text-xs font-mono text-slate-400 uppercase block">
                INSTRUCTION MANEUVERS
              </span>
              {route.steps.map((step, idx) => (
                <div
                  key={step.id || idx}
                  className="p-3 rounded bg-slate-900/60 border border-slate-800 hover:border-slate-700 flex items-start space-x-3 text-xs transition-colors"
                >
                  <div className="w-6 h-6 rounded bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0 mt-0.5">
                    {getTurnIcon(step.turnType)}
                  </div>
                  <div className="w-full">
                    <div className="font-semibold text-slate-100 leading-snug">
                      {step.instruction}
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono mt-1 pt-1 border-t border-slate-800/40">
                      <span>{step.roadName}</span>
                      <span className="text-cyan-400 font-bold">
                        {formatDistance(step.distanceMeters)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          /* Initial Empty State */
          <div className="mt-8 flex flex-col items-center justify-center text-center p-6 rounded-lg bg-slate-900/30 border border-slate-800/60 space-y-3">
            <div className="w-12 h-12 rounded-full bg-slate-800/80 border border-slate-700/80 flex items-center justify-center text-slate-400">
              <MapPin className="w-6 h-6 text-slate-500" />
            </div>

            <div>
              <div className="font-mono font-bold text-slate-200 text-sm tracking-wide">
                NO ROUTE CALCULATED
              </div>
              <p className="text-xs text-slate-400 mt-1 max-w-xs leading-relaxed">
                Select a starting point and destination to calculate an emergency rescue route.
              </p>
            </div>

            <div className="pt-2">
              <span className="text-[10px] font-mono px-2.5 py-1 rounded bg-slate-800 text-slate-400 border border-slate-700">
                AWAITING MAP TARGETS
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Footer Note */}
      <div className="pt-4 border-t border-slate-800/80 text-[11px] font-mono text-slate-400 flex items-center space-x-2">
        <AlertCircle className="w-4 h-4 text-cyan-400 shrink-0" />
        <span>
          {isAiActive
            ? 'Connected to RESQROUTE AI U-Net + Dijkstra Routing Engine.'
            : 'Connected to OSRM real road navigation engine.'}
        </span>
      </div>
    </div>
  );
};
