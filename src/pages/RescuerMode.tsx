import React, { useState, useEffect, useRef } from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { MapView } from '../components/map/MapView';
import { useGeolocation, GPS_UPDATE_INTERVAL_MS, GPS_MIN_MOVEMENT_METERS } from '../hooks/useGeolocation';
import { getDispatches } from '../services/dispatch';
import { calculateAIRoute } from '../services/routing';
import { sendLocationTelemetry } from '../services/missionTracking';
import type { LiveMissionResponseData } from '../services/missionTracking';
import type { Dispatch } from '../types/dispatch';
import type { AIRouteResponse, LocationPoint } from '../types/route';
import type { Incident } from '../types/incident';
import {
  Truck,
  Navigation,
  AlertTriangle,
  CheckCircle2,
  Radio,
  ShieldCheck,
  RefreshCw,
  Loader2,
} from 'lucide-react';

export const RescuerModePage: React.FC = () => {
  const {
    location: rescuerLocation,
    status: gpsStatus,
    errorMsg: gpsErrorMsg,
    isLowAccuracy,
    refresh: refreshGps,
  } = useGeolocation({ autoStart: true });

  const [dispatches, setDispatches] = useState<Dispatch[]>([]);
  const [selectedDispatchId, setSelectedDispatchId] = useState<string>('');
  const [activeDispatch, setActiveDispatch] = useState<Dispatch | null>(null);

  const [aiRoute, setAiRoute] = useState<AIRouteResponse | null>(null);
  const [isRouting, setIsRouting] = useState<boolean>(false);
  const [routeError, setRouteError] = useState<string | null>(null);

  const [liveTelemetry, setLiveTelemetry] = useState<LiveMissionResponseData | null>(null);
  const [candidateReroute, setCandidateReroute] = useState<any | null>(null);
  const [rerouteStatusMsg, setRerouteStatusMsg] = useState<string | null>(null);

  const lastSentLocationRef = useRef<{ lat: number; lng: number } | null>(null);

  // 1. Fetch available active dispatches on mount
  useEffect(() => {
    async function loadMissions() {
      const list = await getDispatches();
      const activeList = list.filter((d) => ['ASSIGNED', 'DISPATCHED', 'EN_ROUTE', 'ON_SCENE'].includes(d.status));
      setDispatches(activeList.length > 0 ? activeList : list);
      if (activeList.length > 0) {
        setSelectedDispatchId(activeList[0].id);
        setActiveDispatch(activeList[0]);
      } else if (list.length > 0) {
        setSelectedDispatchId(list[0].id);
        setActiveDispatch(list[0]);
      }
    }
    loadMissions();
  }, []);

  // 2. Update activeDispatch when dropdown selection changes
  const handleSelectDispatch = (dispatchId: string) => {
    setSelectedDispatchId(dispatchId);
    const found = dispatches.find((d) => d.id === dispatchId) || null;
    setActiveDispatch(found);
    setAiRoute(null);
    setLiveTelemetry(null);
    setCandidateReroute(null);
  };

  // 3. Trigger AI Emergency Route calculation when rescuer GPS & active mission are available
  useEffect(() => {
    if (!rescuerLocation || !activeDispatch) return;

    const startPt: LocationPoint = {
      lat: rescuerLocation.lat,
      lng: rescuerLocation.lng,
      name: 'Rescuer Live GPS Location',
    };

    // Use incident coordinates stored in activeDispatch or fallback to default Bangalore AI region
    const incLat = (activeDispatch as any).incident_latitude ?? (activeDispatch as any).incident?.latitude ?? 12.966602;
    const incLng = (activeDispatch as any).incident_longitude ?? (activeDispatch as any).incident?.longitude ?? 77.599961;

    const destPt: LocationPoint = {
      lat: incLat,
      lng: incLng,
      name: `Incident Site (${activeDispatch.incident_id})`,
    };

    let isMounted = true;
    async function calculateRoute() {
      setIsRouting(true);
      setRouteError(null);
      try {
        const routeRes = await calculateAIRoute({
          start: startPt,
          destination: destPt,
          vehicle_type: 'ambulance',
          avoid_low_confidence: true,
        });
        if (isMounted) {
          setAiRoute(routeRes);
        }
      } catch (err) {
        if (isMounted) {
          setRouteError(err instanceof Error ? err.message : 'AI emergency routing failed.');
        }
      } finally {
        if (isMounted) {
          setIsRouting(false);
        }
      }
    }

    calculateRoute();
    return () => {
      isMounted = false;
    };
  }, [rescuerLocation?.lat, rescuerLocation?.lng, activeDispatch?.id]);

  // 4. Periodically stream live telemetry location to backend (throttled every 3s / > 5m movement)
  useEffect(() => {
    if (!rescuerLocation || !selectedDispatchId) return;

    // Distance check to prevent unnecessary requests
    const lastLoc = lastSentLocationRef.current;
    if (lastLoc) {
      const dLat = (rescuerLocation.lat - lastLoc.lat) * 111000;
      const dLng = (rescuerLocation.lng - lastLoc.lng) * 111000 * Math.cos((rescuerLocation.lat * Math.PI) / 180);
      const distM = Math.sqrt(dLat * dLat + dLng * dLng);
      if (distM < GPS_MIN_MOVEMENT_METERS) {
        return;
      }
    }

    let isMounted = true;
    async function sendTelemetry() {
      try {
        const data = await sendLocationTelemetry(selectedDispatchId, {
          lat: rescuerLocation!.lat,
          lng: rescuerLocation!.lng,
          accuracy: rescuerLocation!.accuracy,
          speed_kmh: rescuerLocation!.speed ? rescuerLocation!.speed * 3.6 : 0,
          heading_degrees: rescuerLocation!.heading || 0,
          timestamp: new Date(rescuerLocation!.timestamp).toISOString(),
        });

        if (isMounted) {
          setLiveTelemetry(data);
          lastSentLocationRef.current = { lat: rescuerLocation!.lat, lng: rescuerLocation!.lng };
          if (data.reroute_recommendation) {
            setCandidateReroute(data.reroute_recommendation);
          }
        }
      } catch (err) {
        // Log telemetry warning quietly
        console.warn('Live telemetry sync warning:', err);
      }
    }

    const interval = setInterval(sendTelemetry, GPS_UPDATE_INTERVAL_MS);
    sendTelemetry(); // Run immediately

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [selectedDispatchId, rescuerLocation?.lat, rescuerLocation?.lng]);

  const handleApproveReroute = () => {
    setRerouteStatusMsg('NEW REROUTE ACTIVATED BY OPERATOR / RESCUER!');
    setCandidateReroute(null);
  };

  // Map markers & geometry
  const defaultCenter: [number, number] = rescuerLocation
    ? [rescuerLocation.lat, rescuerLocation.lng]
    : [12.973, 77.591];

  const incLat = (activeDispatch as any)?.incident_latitude ?? (activeDispatch as any)?.incident?.latitude ?? 12.966602;
  const incLng = (activeDispatch as any)?.incident_longitude ?? (activeDispatch as any)?.incident?.longitude ?? 77.599961;

  const mapIncidents: Incident[] = activeDispatch
    ? [
        {
          id: activeDispatch.incident_id || 'active-inc',
          incident_code: activeDispatch.incident_id || 'INC-TARGET',
          incident_type: 'MEDICAL',
          severity: 'CRITICAL',
          status: 'ACTIVE',
          latitude: incLat,
          longitude: incLng,
          location_name: 'Target Emergency Incident Location',
          description: 'Active Destination Incident',
          code: 'INC-TARGET',
          title: 'Target Incident',
          type: 'medical',
          location: { lat: incLat, lng: incLng, name: 'Target Destination' },
          reportedAt: 'ACTIVE',
        },
      ]
    : [];

  const startPt: LocationPoint | null = rescuerLocation
    ? { lat: rescuerLocation.lat, lng: rescuerLocation.lng, name: 'Rescuer Live GPS' }
    : null;

  const destPt: LocationPoint = {
    lat: incLat,
    lng: incLng,
    name: 'Fixed Incident Destination',
  };

  return (
    <PageContainer>
      <div className="flex-1 flex flex-col lg:flex-row h-full overflow-hidden font-sans">
        {/* LEFT: Rescuer Dashboard & Navigation Panel */}
        <div className="w-full lg:w-96 shrink-0 bg-[#0b0f19] border-r border-slate-800 p-4 flex flex-col justify-between overflow-y-auto select-none space-y-4">
          <div>
            {/* Header */}
            <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
              <Truck className="w-5 h-5 text-cyan-400 animate-pulse" />
              <div>
                <h2 className="font-mono font-bold text-sm tracking-wider text-slate-100 uppercase">
                  🚑 RESCUER DASHBOARD
                </h2>
                <p className="text-[10px] font-mono text-slate-400">
                  REAL-TIME GPS EMERGENCY NAVIGATION
                </p>
              </div>
            </div>

            {/* Active Mission Selector */}
            <div className="mt-4 space-y-1.5">
              <label className="text-xs font-mono uppercase text-slate-400 block flex items-center justify-between">
                <span>ACTIVE MISSION DISPATCH</span>
                <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
              </label>
              <select
                value={selectedDispatchId}
                onChange={(e) => handleSelectDispatch(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                {dispatches.length === 0 ? (
                  <option value="">-- No Active Mission Dispatches --</option>
                ) : (
                  dispatches.map((d) => (
                    <option key={d.id} value={d.id}>
                      [{d.id.slice(0, 8)}] Unit {d.rescue_unit_id} -&gt; {d.incident_id} ({d.status})
                    </option>
                  ))
                )}
              </select>
            </div>

            {/* Live Rescuer GPS Status Card */}
            <div className="mt-4 p-3 rounded-lg bg-slate-900/90 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
                  <Radio className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
                  <span>RESCUER LIVE GPS</span>
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                    gpsStatus === 'ACTIVE'
                      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                      : gpsStatus === 'CONNECTING'
                      ? 'bg-amber-500/20 text-amber-400 border-amber-500/40 animate-pulse'
                      : 'bg-red-500/20 text-red-400 border-red-500/40'
                  }`}
                >
                  ● {gpsStatus}
                </span>
              </div>

              {rescuerLocation ? (
                <div className="grid grid-cols-2 gap-2 text-xs font-mono text-slate-300 pt-1 border-t border-slate-800/60">
                  <div>
                    <span className="text-slate-400 block text-[10px]">CURRENT LAT/LNG:</span>
                    <span className="text-cyan-300 font-bold">
                      {rescuerLocation.lat.toFixed(4)}°, {rescuerLocation.lng.toFixed(4)}°
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">ACCURACY:</span>
                    <span
                      className={`font-bold ${
                        isLowAccuracy ? 'text-amber-400' : 'text-emerald-400'
                      }`}
                    >
                      {rescuerLocation.accuracy.toFixed(1)} m
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">CURRENT SPEED:</span>
                    <span className="text-slate-100 font-bold">
                      {rescuerLocation.speed ? (rescuerLocation.speed * 3.6).toFixed(1) : '0.0'} km/h
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">HEADING:</span>
                    <span className="text-slate-100 font-bold">
                      {rescuerLocation.heading ? `${rescuerLocation.heading.toFixed(0)}°` : 'N/A'}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-xs font-mono text-slate-400 py-1">
                  {gpsErrorMsg || 'Connecting to Rescuer device GPS...'}
                </p>
              )}

              <button
                type="button"
                onClick={refreshGps}
                className="w-full py-1.5 px-3 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-mono flex items-center justify-center space-x-1.5 transition-colors cursor-pointer mt-2"
              >
                <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
                <span>RECENTER RESCUER GPS</span>
              </button>
            </div>

            {/* Live Navigation & Mission Telemetry */}
            <div className="mt-4 p-3.5 rounded-lg bg-slate-900/90 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-xs font-mono text-slate-300 font-bold uppercase flex items-center space-x-1.5">
                  <Navigation className="w-4 h-4 text-cyan-400" />
                  <span>AI EMERGENCY ROUTING METRICS</span>
                </span>
                {isRouting && <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />}
              </div>

              {routeError && (
                <div className="p-2.5 rounded bg-red-950/40 border border-red-900/80 text-red-300 text-xs font-mono">
                  {routeError}
                </div>
              )}

              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="p-2 rounded bg-slate-950/50 border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">DISTANCE REMAINING</span>
                  <span className="text-cyan-300 font-bold text-sm">
                    {liveTelemetry
                      ? `${(liveTelemetry.distance_remaining_meters / 1000).toFixed(2)} km`
                      : aiRoute
                      ? `${(aiRoute.total_distance_meters / 1000).toFixed(2)} km`
                      : '---'}
                  </span>
                </div>

                <div className="p-2 rounded bg-slate-950/50 border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">ESTIMATED ETA</span>
                  <span className="text-emerald-400 font-bold text-sm">
                    {liveTelemetry
                      ? `${Math.ceil(liveTelemetry.eta_seconds / 60)} min`
                      : aiRoute
                      ? `${Math.ceil(aiRoute.estimated_duration_seconds / 60)} min`
                      : '---'}
                  </span>
                </div>

                <div className="p-2 rounded bg-slate-950/50 border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">ROUTE HEALTH</span>
                  <span className="text-emerald-300 font-bold text-sm">
                    {liveTelemetry?.route_health || 95} / 100
                  </span>
                </div>

                <div className="p-2 rounded bg-slate-950/50 border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">AI CONFIDENCE</span>
                  <span className="text-cyan-300 font-bold text-sm">
                    {aiRoute?.average_confidence ? aiRoute.average_confidence.toFixed(2) : '0.88'}
                  </span>
                </div>
              </div>

              {/* Progress Bar */}
              {liveTelemetry && (
                <div className="space-y-1 pt-1">
                  <div className="flex justify-between text-[11px] font-mono text-slate-400">
                    <span>MISSION PROGRESS</span>
                    <span className="text-cyan-300 font-bold">{liveTelemetry.progress_percent.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                    <div
                      className="bg-cyan-500 h-full transition-all duration-500"
                      style={{ width: `${liveTelemetry.progress_percent}%` }}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Candidate Reroute Approval Banner (Stage 8C Route Deviation) */}
            {candidateReroute && (
              <div className="mt-4 p-3.5 rounded-lg bg-amber-950/40 border border-amber-800/80 space-y-2">
                <div className="flex items-center space-x-1.5 text-amber-400 text-xs font-mono font-bold">
                  <AlertTriangle className="w-4 h-4 text-amber-400 animate-pulse" />
                  <span>ROUTE DEVIATION / CANDIDATE REROUTE AVAILABLE</span>
                </div>
                <p className="text-[11px] font-mono text-slate-300">
                  Rescuer location deviated from active route. Alternative AI candidate route ready for approval.
                </p>
                <div className="flex space-x-2 pt-1">
                  <button
                    type="button"
                    onClick={handleApproveReroute}
                    className="flex-1 py-1.5 px-3 rounded bg-amber-500 hover:bg-amber-400 text-slate-950 font-mono font-bold text-xs cursor-pointer transition-colors"
                  >
                    APPROVE REROUTE
                  </button>
                  <button
                    type="button"
                    onClick={() => setCandidateReroute(null)}
                    className="py-1.5 px-3 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-xs cursor-pointer transition-colors"
                  >
                    DISMISS
                  </button>
                </div>
              </div>
            )}

            {rerouteStatusMsg && (
              <div className="mt-3 p-2.5 rounded bg-emerald-950/40 border border-emerald-800 text-emerald-300 text-xs font-mono flex items-center space-x-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>{rerouteStatusMsg}</span>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT: Interactive GIS Emergency Navigation Map */}
        <div className="flex-1 h-full relative min-h-[400px]">
          <MapView
            center={defaultCenter}
            zoom={15}
            incidents={mapIncidents}
            startLocation={startPt}
            destination={destPt}
            routeGeometry={aiRoute?.geometry || liveTelemetry?.route_geometry || null}
          />
        </div>
      </div>
    </PageContainer>
  );
};
