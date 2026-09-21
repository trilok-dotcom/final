import React, { useState, useEffect } from 'react';
import type { DispatchResponse, Dispatch } from '../../types/dispatch';
import type { LiveMission, MissionWebSocketMessage } from '../../types/mission';
import type { RouteHealthStatus, RerouteRecommendation } from '../../types/rerouting';
import { updateDispatchStatus } from '../../services/dispatch';
import {
  connectMissionWebSocket,
  getLiveMission,
  startMissionSimulation,
  stopMissionSimulation,
} from '../../services/missionTracking';
import { evaluateRouteHealth, evaluateReroute } from '../../services/rerouting';
import { RouteHealthPanel } from './RouteHealthPanel';
import {
  Navigation,
  MapPin,
  Cpu,
  CheckCircle2,
  Loader2,
  Zap,
  Play,
  Square,
  Activity,
  Compass,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  X,
} from 'lucide-react';
import { formatDistance, formatDuration } from '../../lib/utils';

interface ActiveMissionPanelProps {
  dispatchData: DispatchResponse | Dispatch;
  onStatusChange?: (updatedDispatch: Dispatch) => void;
  onRerouteApproved?: (newRouteId: string) => void;
  onClose?: () => void;
}

export const ActiveMissionPanel: React.FC<ActiveMissionPanelProps> = ({
  dispatchData,
  onStatusChange,
  onRerouteApproved,
  onClose,
}) => {
  const dispatchId = 'dispatch_id' in dispatchData ? dispatchData.dispatch_id : dispatchData.id;

  const [updating, setUpdating] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [liveMission, setLiveMission] = useState<LiveMission | null>(null);
  const [currentStatus, setCurrentStatus] = useState<string>(
    dispatchData.status.toUpperCase()
  );

  // Stage 8C Route Health State
  const [routeHealthStatus, setRouteHealthStatus] = useState<RouteHealthStatus>('HEALTHY');
  const [rerouteRecommendation, setRerouteRecommendation] = useState<RerouteRecommendation | null>(null);
  const [showHealthModal, setShowHealthModal] = useState(false);

  // Load initial route health
  useEffect(() => {
    let isMounted = true;

    const checkHealth = async () => {
      try {
        const health = await evaluateRouteHealth(dispatchId);
        if (isMounted) {
          setRouteHealthStatus(health.route_health);
        }
        const rec = await evaluateReroute(dispatchId);
        if (isMounted) {
          setRerouteRecommendation(rec);
        }
      } catch {
        // Fallback
      }
    };
    checkHealth();

    return () => {
      isMounted = false;
    };
  }, [dispatchId]);

  // Load initial live telemetry and subscribe to WebSocket stream
  useEffect(() => {
    let isMounted = true;

    const fetchInitial = async () => {
      try {
        const live = await getLiveMission(dispatchId);
        if (isMounted) {
          setLiveMission(live);
          setCurrentStatus(live.status.toUpperCase());
        }
      } catch {
        // Fallback
      }
    };
    fetchInitial();

    const unsubscribe = connectMissionWebSocket((msg: MissionWebSocketMessage | any) => {
      if (msg.dispatch_id === dispatchId && isMounted) {
        if (msg.status) setCurrentStatus(msg.status.toUpperCase());

        // Handle ROUTE_UPDATED WebSocket notification
        if (msg.event === 'ROUTE_UPDATED') {
          setRouteHealthStatus('HEALTHY');
          setRerouteRecommendation(null);
          setShowHealthModal(false);

          setLiveMission((prev) => {
            if (!prev) return null;
            return {
              ...prev,
              distance_remaining_meters: msg.distance_remaining_meters ?? prev.distance_remaining_meters,
              eta_seconds: msg.eta_seconds ?? prev.eta_seconds,
              average_ai_confidence: msg.confidence ?? prev.average_ai_confidence,
              risk_level: msg.risk_level ?? prev.risk_level,
            };
          });

          if (onRerouteApproved && msg.new_route_id) {
            onRerouteApproved(msg.new_route_id);
          }
        }

        // Update live telemetry metrics
        setLiveMission((prev) => {
          if (!prev) return null;
          return {
            ...prev,
            status: msg.status || prev.status,
            distance_remaining_meters: msg.distance_remaining_meters ?? prev.distance_remaining_meters,
            eta_seconds: msg.eta_seconds ?? prev.eta_seconds,
            progress_percent: msg.progress_percent ?? prev.progress_percent,
            unit: {
              ...prev.unit,
              lat: msg.location?.lat ?? prev.unit.lat,
              lng: msg.location?.lng ?? prev.unit.lng,
              speed_kmh: msg.speed_kmh ?? prev.unit.speed_kmh,
              heading_degrees: msg.heading_degrees ?? prev.unit.heading_degrees,
            },
          };
        });
      }
    });

    return () => {
      isMounted = false;
      unsubscribe();
    };
  }, [dispatchId, onRerouteApproved]);

  const handleNextState = async (targetState: string) => {
    setUpdating(true);
    try {
      const updated = await updateDispatchStatus(dispatchId, targetState);
      setCurrentStatus(updated.status.toUpperCase());
      if (onStatusChange) onStatusChange(updated);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update mission status');
    } finally {
      setUpdating(false);
    }
  };

  const handleStartSim = async () => {
    setUpdating(true);
    try {
      await startMissionSimulation(dispatchId);
      setIsSimulating(true);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to start movement simulation');
    } finally {
      setUpdating(false);
    }
  };

  const handleStopSim = async () => {
    setUpdating(true);
    try {
      await stopMissionSimulation(dispatchId);
      setIsSimulating(false);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to stop movement simulation');
    } finally {
      setUpdating(false);
    }
  };

  // Metrics extraction
  const route = 'route' in dispatchData ? dispatchData.route : null;
  const distRem = liveMission?.distance_remaining_meters ?? route?.distance_meters ?? 0;
  const etaSec = liveMission?.eta_seconds ?? route?.estimated_duration_seconds ?? 0;
  const progressPct = liveMission?.progress_percent ?? 0;
  const speedKmh = liveMission?.unit?.speed_kmh ?? 0;
  const headingDeg = liveMission?.unit?.heading_degrees ?? 0;

  const conf = liveMission?.average_ai_confidence ?? route?.average_confidence ?? 0.86;
  const risk = liveMission?.risk_level ?? route?.risk_level ?? 'low';
  const unitCode = liveMission?.unit?.code ?? ('rescue_unit_code' in dispatchData ? dispatchData.rescue_unit_code : 'AMB-01');
  const unitName = liveMission?.unit?.name ?? ('rescue_unit_name' in dispatchData ? dispatchData.rescue_unit_name : 'Rescue Unit');
  const vehicle = liveMission?.unit?.type ?? ('vehicle_type' in dispatchData ? dispatchData.vehicle_type : 'AMBULANCE');

  const getStatusBadge = (st: string) => {
    switch (st) {
      case 'DISPATCHED':
        return 'bg-purple-950/80 text-purple-300 border-purple-800 animate-pulse';
      case 'EN_ROUTE':
        return 'bg-cyan-950/80 text-cyan-300 border-cyan-800 animate-pulse';
      case 'ON_SCENE':
        return 'bg-amber-950/80 text-amber-300 border-amber-800 animate-pulse';
      case 'COMPLETED':
        return 'bg-emerald-950/80 text-emerald-300 border-emerald-800';
      case 'CANCELLED':
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const getStepIndex = (st: string) => {
    switch (st) {
      case 'DISPATCHED':
        return 1;
      case 'EN_ROUTE':
        return 2;
      case 'ON_SCENE':
        return 3;
      case 'COMPLETED':
        return 4;
      default:
        return 1;
    }
  };
  const stepIdx = getStepIndex(currentStatus);

  const isRerouteRecommended =
    rerouteRecommendation?.decision === 'REROUTE_RECOMMENDED' ||
    rerouteRecommendation?.decision === 'REROUTE_REQUIRED';

  return (
    <div className="bg-[#0b0f19] border border-cyan-500/40 rounded-lg p-4 font-sans shadow-2xl space-y-3 select-none">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
        <div className="flex items-center space-x-2">
          <Zap className="w-4 h-4 text-cyan-400 animate-pulse" />
          <h3 className="font-mono font-bold text-xs tracking-wider text-slate-100 uppercase">
            LIVE MISSION COMMAND & CONTROL
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded border ${getStatusBadge(
              currentStatus
            )}`}
          >
            {currentStatus.replace('_', ' ')}
          </span>
          {onClose && (
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition"
              title="Close Panel"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Stage 8C ROUTE HEALTH INDICATOR & RE-ROUTE ALERT BANNER */}
      <div className="flex items-center justify-between bg-slate-900/90 border border-slate-800 rounded px-3 py-2 font-mono text-xs">
        <div className="flex items-center space-x-2">
          <span className="text-slate-400 uppercase text-[10px] font-bold">ROUTE HEALTH:</span>
          {routeHealthStatus === 'HEALTHY' ? (
            <span className="text-emerald-400 font-bold flex items-center space-x-1">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping inline-block"></span>
              <span>● HEALTHY</span>
            </span>
          ) : routeHealthStatus === 'DEGRADED' ? (
            <span className="text-amber-400 font-bold flex items-center space-x-1">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>⚠ DEGRADED</span>
            </span>
          ) : (
            <span className="text-red-400 font-bold flex items-center space-x-1">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>⚠ CRITICAL</span>
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={() => setShowHealthModal(!showHealthModal)}
          className="text-[10px] font-bold px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-cyan-500/30 flex items-center space-x-1"
        >
          <span>ROUTE HEALTH PANEL</span>
          {showHealthModal ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>
      </div>

      {/* Recommended Reroute Banner */}
      {isRerouteRecommended && !showHealthModal && (
        <div className="bg-amber-950/60 border border-amber-500/80 rounded-lg p-3 flex items-center justify-between space-x-2 animate-pulse">
          <div className="flex items-center space-x-2 text-amber-200 font-mono text-xs font-bold">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>⚠ AI RE-ROUTE RECOMMENDED</span>
          </div>
          <button
            type="button"
            onClick={() => setShowHealthModal(true)}
            className="px-3 py-1 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded font-mono font-bold text-xs uppercase transition-colors"
          >
            REVIEW
          </button>
        </div>
      )}

      {/* Expanded Route Health Assessment Panel */}
      {showHealthModal && (
        <RouteHealthPanel
          dispatchId={dispatchId}
          onRerouteApproved={(newRouteId) => {
            if (onRerouteApproved) onRerouteApproved(newRouteId);
            setShowHealthModal(false);
          }}
        />
      )}

      {/* EMERGENCY MISSION PROGRESS BAR */}
      <div className="bg-slate-900/90 border border-slate-800 rounded p-2.5 space-y-1.5 font-mono">
        <div className="flex items-center justify-between text-[10px] font-bold">
          <span className={stepIdx >= 1 ? 'text-purple-400' : 'text-slate-600'}>1. DISPATCHED</span>
          <span className={stepIdx >= 2 ? 'text-cyan-400' : 'text-slate-600'}>2. EN ROUTE</span>
          <span className={stepIdx >= 3 ? 'text-amber-400' : 'text-slate-600'}>3. ON SCENE</span>
          <span className={stepIdx >= 4 ? 'text-emerald-400' : 'text-slate-600'}>4. COMPLETED</span>
        </div>
        <div className="w-full h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-800 relative">
          <div
            className="h-full bg-gradient-to-r from-purple-500 via-cyan-400 to-emerald-400 transition-all duration-500"
            style={{ width: `${Math.max(5, progressPct)}%` }}
          />
        </div>
        <div className="flex items-center justify-between text-[10px] text-slate-400 pt-0.5">
          <span>PROGRESS: {progressPct.toFixed(1)}%</span>
          <span className="flex items-center space-x-1">
            <Activity className="w-3 h-3 text-cyan-400" />
            <span>SPEED: {speedKmh.toFixed(1)} KM/H</span>
          </span>
        </div>
      </div>

      {/* Unit & Vehicle Details */}
      <div className="grid grid-cols-2 gap-2 text-xs font-mono">
        <div className="p-2 rounded bg-slate-900/80 border border-slate-800 space-y-0.5">
          <span className="text-[10px] text-slate-400 uppercase block">RESPONDING UNIT</span>
          <div className="font-bold text-cyan-300">{unitCode}</div>
          <div className="text-[10px] text-slate-400 truncate">{unitName}</div>
        </div>

        <div className="p-2 rounded bg-slate-900/80 border border-slate-800 space-y-0.5">
          <span className="text-[10px] text-slate-400 uppercase block">VEHICLE & HEADING</span>
          <div className="font-bold text-slate-200 uppercase">{vehicle?.replace('_', ' ')}</div>
          <div className="text-[10px] text-emerald-400 flex items-center space-x-1">
            <Compass className="w-3 h-3" />
            <span>HEADING: {headingDeg.toFixed(0)}°</span>
          </div>
        </div>
      </div>

      {/* Route Telemetry & ETA Metrics */}
      <div className="p-3 rounded bg-cyan-950/20 border border-cyan-900/40 space-y-2 font-mono text-xs">
        <div className="flex items-center justify-between">
          <span className="text-slate-400">DISTANCE REMAINING:</span>
          <span className="text-cyan-300 font-bold">{formatDistance(distRem)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400">CURRENT ETA:</span>
          <span className="text-cyan-300 font-bold">{formatDuration(etaSec)}</span>
        </div>
        <div className="flex items-center justify-between pt-1 border-t border-cyan-900/30">
          <span className="text-slate-400">AI ROAD CONFIDENCE:</span>
          <span className="text-emerald-400 font-bold">{(conf * 100).toFixed(1)}%</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400">ROAD CONFIDENCE RISK:</span>
          <span
            className={`font-bold uppercase px-1.5 py-0.2 rounded text-[10px] ${
              risk.toLowerCase() === 'low'
                ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                : 'bg-amber-950 text-amber-300 border border-amber-800'
            }`}
          >
            {risk}
          </span>
        </div>
      </div>

      {/* SIMULATION CONTROLS */}
      {currentStatus !== 'COMPLETED' && currentStatus !== 'CANCELLED' && (
        <div className="p-2.5 rounded bg-slate-900/90 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between font-mono text-[10px]">
            <span className="text-slate-400 uppercase font-bold flex items-center space-x-1">
              <Cpu className="w-3.5 h-3.5 text-cyan-400" />
              <span>LIVE AI MOVEMENT SIMULATOR</span>
            </span>
            <span className="text-cyan-400 font-bold">REAL-TIME GRAPH</span>
          </div>

          <div className="flex items-center space-x-2">
            {!isSimulating ? (
              <button
                type="button"
                disabled={updating}
                onClick={handleStartSim}
                className="flex-1 py-1.5 px-3 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-mono font-bold text-xs rounded uppercase flex items-center justify-center space-x-1.5 transition-colors cursor-pointer"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>START LIVE SIMULATION</span>
              </button>
            ) : (
              <button
                type="button"
                disabled={updating}
                onClick={handleStopSim}
                className="flex-1 py-1.5 px-3 bg-amber-600 hover:bg-amber-500 text-slate-950 font-mono font-bold text-xs rounded uppercase flex items-center justify-center space-x-1.5 transition-colors cursor-pointer"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
                <span>STOP SIMULATION</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Mission State Progression Actions */}
      <div className="pt-1">
        {currentStatus === 'DISPATCHED' && (
          <button
            type="button"
            disabled={updating}
            onClick={() => handleNextState('EN_ROUTE')}
            className="w-full py-2 px-3 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-mono font-bold text-xs rounded uppercase flex items-center justify-center space-x-2 shadow-lg cursor-pointer"
          >
            {updating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Navigation className="w-3.5 h-3.5" />}
            <span>START MISSION (EN ROUTE)</span>
          </button>
        )}

        {currentStatus === 'EN_ROUTE' && (
          <button
            type="button"
            disabled={updating}
            onClick={() => handleNextState('ON_SCENE')}
            className="w-full py-2 px-3 bg-amber-500 hover:bg-amber-400 text-slate-950 font-mono font-bold text-xs rounded uppercase flex items-center justify-center space-x-2 shadow-lg cursor-pointer"
          >
            {updating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <MapPin className="w-3.5 h-3.5" />}
            <span>MARK ARRIVED (ON SCENE)</span>
          </button>
        )}

        {currentStatus === 'ON_SCENE' && (
          <button
            type="button"
            disabled={updating}
            onClick={() => handleNextState('COMPLETED')}
            className="w-full py-2 px-3 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-mono font-bold text-xs rounded uppercase flex items-center justify-center space-x-2 shadow-lg cursor-pointer"
          >
            {updating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
            <span>COMPLETE MISSION & RELEASE UNIT</span>
          </button>
        )}

        {currentStatus === 'COMPLETED' && (
          <div className="p-2 rounded bg-emerald-950/40 border border-emerald-800 text-emerald-300 font-mono text-xs flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>MISSION COMPLETED. RESCUE UNIT RELEASED BACK TO STANDBY.</span>
          </div>
        )}
      </div>
    </div>
  );
};
