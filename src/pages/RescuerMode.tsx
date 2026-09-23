import React, { useState, useEffect, useRef, useCallback } from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { MapView } from '../components/map/MapView';
import { useGeolocation, GPS_UPDATE_INTERVAL_MS, GPS_MIN_MOVEMENT_METERS } from '../hooks/useGeolocation';
import { getDispatches } from '../services/dispatch';
import { getIncidents } from '../services/incidents';
import { calculateAIRoute } from '../services/routing';
import { sendLocationTelemetry } from '../services/missionTracking';
import type { LiveMissionResponseData } from '../services/missionTracking';
import type { AIRouteResponse, LocationPoint, RouteStepDetail } from '../types/route';

import type { Incident, EmergencyIncident } from '../types/incident';
import {
  Truck,
  Navigation,
  AlertTriangle,
  CheckCircle2,
  Radio,
  RefreshCw,
  Loader2,
  Target,
  MapPin,
  Compass,
  ArrowUp,
  CornerUpLeft,
  CornerUpRight,
} from 'lucide-react';
import {
  haversineDistanceMeters,
  distanceToPolylineMeters,
  getGpsAccuracyStatus,
  formatDistance,
  formatDuration,
} from '../lib/utils';

export const RescuerModePage: React.FC = () => {
  const {
    location: rescuerLocation,
    status: gpsStatus,
    errorMsg: gpsErrorMsg,
    refresh: refreshGps,
  } = useGeolocation({ autoStart: true });

  const [incidentsList, setIncidentsList] = useState<EmergencyIncident[]>([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [selectedDispatchId, setSelectedDispatchId] = useState<string>('');
  const [customDestination, setCustomDestination] = useState<LocationPoint | null>(null);

  const [aiRoute, setAiRoute] = useState<AIRouteResponse | null>(null);
  const [isRouting, setIsRouting] = useState<boolean>(false);
  const [isRerouting, setIsRerouting] = useState<boolean>(false);
  const [routeError, setRouteError] = useState<string | null>(null);

  // Turn-by-Turn Navigation Engine State
  const [isArrived, setIsArrived] = useState<boolean>(false);
  const [isOffRoute, setIsOffRoute] = useState<boolean>(false);
  const [offRouteDistance, setOffRouteDistance] = useState<number>(0);
  const [remainingDistMeters, setRemainingDistMeters] = useState<number>(0);
  const [remainingDurationSecs, setRemainingDurationSecs] = useState<number>(0);
  const [currentStepIdx, setCurrentStepIdx] = useState<number>(0);
  const [distToManeuverMeters, setDistToManeuverMeters] = useState<number>(0);

  const [mapCenter, setMapCenter] = useState<[number, number]>([12.973, 77.591]);
  const [mapZoom, setMapZoom] = useState<number>(14);

  const [liveTelemetry, setLiveTelemetry] = useState<LiveMissionResponseData | null>(null);
  const [rerouteStatusMsg, setRerouteStatusMsg] = useState<string | null>(null);


  const lastSentLocationRef = useRef<{ lat: number; lng: number } | null>(null);
  const isRoutingRef = useRef<boolean>(false);

  // 1. Load active dispatches & emergency incidents on mount
  useEffect(() => {
    async function loadMissionsAndIncidents() {
      try {
        const [list, incList] = await Promise.all([getDispatches(), getIncidents()]);
        const activeList = list.filter((d) => ['ASSIGNED', 'DISPATCHED', 'EN_ROUTE', 'ON_SCENE'].includes(d.status));
        setIncidentsList(incList);

        if (incList.length > 0) {
          // Default select the first active rescue request
          const firstInc = incList[0];
          setSelectedIncidentId(firstInc.id);
          const incLat = firstInc.latitude || firstInc.location?.lat || 12.966602;
          const incLng = firstInc.longitude || firstInc.location?.lng || 77.599961;
          setCustomDestination({
            lat: incLat,
            lng: incLng,
            name: firstInc.title || firstInc.incident_code || firstInc.location_name || `Incident ${firstInc.id}`,
          });
        } else if (activeList.length > 0) {
          setSelectedDispatchId(activeList[0].id);
        }

      } catch {
        // Fallback gracefully
      }
    }
    loadMissionsAndIncidents();
  }, []);

  // 2. Selected Incident Object
  const selectedIncident = incidentsList.find((i) => i.id === selectedIncidentId) || null;

  // 3. Core Route Calculation Function
  const triggerRouteCalculation = useCallback(
    async (startPt: LocationPoint, destPt: LocationPoint, isRerouteCall = false) => {
      if (isRoutingRef.current) return;
      isRoutingRef.current = true;

      if (isRerouteCall) {
        setIsRerouting(true);
      } else {
        setIsRouting(true);
      }
      setRouteError(null);

      try {
        const routeRes = await calculateAIRoute({
          start: startPt,
          destination: destPt,
          vehicle_type: 'ambulance',
          avoid_low_confidence: true,
        });

        setAiRoute(routeRes);
        setIsArrived(false);
        setIsOffRoute(false);
        setOffRouteDistance(0);

        // Calculate initial metrics
        const totalDist = routeRes.total_distance_meters || 0;
        const totalDur = routeRes.estimated_duration_seconds || 0;
        setRemainingDistMeters(totalDist);
        setRemainingDurationSecs(totalDur);
        setCurrentStepIdx(0);

        if (routeRes.steps && routeRes.steps.length > 0) {
          setDistToManeuverMeters(routeRes.steps[0].distance_meters || 0);
        }

        // REQUIREMENT 23: CRITICAL DEBUG LOGGING
        console.log('[RESCUER NAVIGATION]', {
          'START GPS': {
            lat: startPt.lat,
            lng: startPt.lng,
            accuracy: rescuerLocation?.accuracy || 0,
          },
          DESTINATION: {
            lat: destPt.lat,
            lng: destPt.lng,
          },
          'SNAPPED START': routeRes.snapped_start,
          'SNAPPED DESTINATION': routeRes.snapped_destination,
          ROUTE: {
            distance: totalDist,
            duration: totalDur,
            geometry_points: routeRes.geometry?.coordinates?.length || 0,
            steps: routeRes.steps?.length || 0,
          },
          'CURRENT STEP': {
            index: 0,
            instruction: routeRes.steps?.[0]?.instruction || 'Start Navigation',
            distance_remaining: totalDist,
          },
          'OFF ROUTE': {
            distance: 0,
          },
        });
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : 'Unable to find a routable road near the current rescuer location.';
        setRouteError(errMsg);
        setAiRoute(null);
        console.warn('[RESCUER NAVIGATION] Route calculation failed:', errMsg);
      } finally {
        setIsRouting(false);
        setIsRerouting(false);
        isRoutingRef.current = false;
      }
    },
    [rescuerLocation?.accuracy]
  );

  // 4. Incident Selection Handler
  const handleSelectIncidentById = (incidentId: string) => {
    const inc = incidentsList.find((i) => i.id === incidentId);
    if (!inc) return;

    setSelectedIncidentId(incidentId);
    const incLat = inc.latitude || inc.location?.lat || 12.966602;
    const incLng = inc.longitude || inc.location?.lng || 77.599961;

    const destPt: LocationPoint = {
      lat: incLat,
      lng: incLng,
      name: inc.title || inc.incident_code || inc.location_name || `Rescue Incident ${inc.id}`,
    };

    setCustomDestination(destPt);
    setIsArrived(false);
    setRerouteStatusMsg(`TARGET INCIDENT SELECTED: ${inc.incident_code || inc.title || inc.id}`);

    const rescuerLat = rescuerLocation?.lat ?? 12.973;
    const rescuerLng = rescuerLocation?.lng ?? 77.591;
    const startPt: LocationPoint = {
      lat: rescuerLat,
      lng: rescuerLng,
      name: 'Current Rescuer Live GPS',
    };

    triggerRouteCalculation(startPt, destPt, false);
  };

  // 4b. Find Nearest Incident Handler
  const handleRouteToNearestIncident = () => {
    if (incidentsList.length === 0) return;

    const curLat = rescuerLocation?.lat ?? 12.973;
    const curLng = rescuerLocation?.lng ?? 77.591;

    let nearest = incidentsList[0];
    let minDistance = Number.MAX_VALUE;

    incidentsList.forEach((inc) => {
      const lat = inc.latitude || inc.location?.lat || 12.973;
      const lng = inc.longitude || inc.location?.lng || 77.591;
      const dist = haversineDistanceMeters(curLat, curLng, lat, lng);
      if (dist < minDistance) {
        minDistance = dist;
        nearest = inc;
      }
    });

    handleSelectIncidentById(nearest.id);
  };

  // 5. Initial Route Request on Mount or Destination Selection
  useEffect(() => {
    if (!customDestination) return;

    const rescuerLat = rescuerLocation?.lat ?? 12.973;
    const rescuerLng = rescuerLocation?.lng ?? 77.591;

    const startPt: LocationPoint = {
      lat: rescuerLat,
      lng: rescuerLng,
      name: 'Rescuer Live Location',
    };

    triggerRouteCalculation(startPt, customDestination, false);
  }, [customDestination?.lat, customDestination?.lng]); // eslint-disable-line react-hooks/exhaustive-deps

  // 6. Dynamic GPS Position Evaluation Engine (Progress, Off-Route & Arrival Detection)
  useEffect(() => {
    if (!rescuerLocation || !customDestination) return;

    const curLat = rescuerLocation.lat;
    const curLng = rescuerLocation.lng;

    // Requirement 20: Arrival Detection (Distance < 30m)
    const distToDest = haversineDistanceMeters(curLat, curLng, customDestination.lat, customDestination.lng);
    if (distToDest < 30.0) {
      if (!isArrived) {
        setIsArrived(true);
        setIsOffRoute(false);
        setRemainingDistMeters(0);
        setRemainingDurationSecs(0);
        console.log('[RESCUER NAVIGATION] ARRIVED AT RESCUE LOCATION');
      }
      return;
    }

    if (isArrived) return; // Do not continuously update or reroute once arrived

    // If active route geometry is present, evaluate progress & off-route status
    if (aiRoute && aiRoute.geometry && aiRoute.geometry.coordinates) {
      const geoCoords = aiRoute.geometry.coordinates;
      const { minDistanceMeters, closestIndex, remainingDistanceMeters } = distanceToPolylineMeters(
        curLat,
        curLng,
        geoCoords
      );

      // Requirement 9: Off-Route Detection (> 50m)
      if (minDistanceMeters > 50.0 && !isRoutingRef.current) {
        setIsOffRoute(true);
        setOffRouteDistance(minDistanceMeters);

        console.warn(`[RESCUER NAVIGATION] OFF ROUTE: distance=${minDistanceMeters.toFixed(1)}m > 50m. REROUTING...`);

        const startPt: LocationPoint = {
          lat: curLat,
          lng: curLng,
          name: 'Current Rescuer Live GPS',
        };

        triggerRouteCalculation(startPt, customDestination, true);
        return;
      }

      // Requirement 8: Update Route Progress
      setIsOffRoute(false);
      setRemainingDistMeters(remainingDistanceMeters);
      const estSpeedMps = (45.0 * 1000.0) / 3600.0;
      setRemainingDurationSecs(Math.round(remainingDistanceMeters / estSpeedMps));

      // Determine step progression
      const steps = aiRoute.steps || [];
      if (steps.length > 0) {
        let activeIdx = 0;
        let minDistToStepLoc = Number.MAX_VALUE;

        // Find current active step based on progress along polyline
        for (let i = 0; i < steps.length; i++) {
          const s = steps[i];
          if (s.location && s.location.length >= 2) {
            const [sLng, sLat] = s.location;
            const dist = haversineDistanceMeters(curLat, curLng, sLat, sLng);
            if (dist < minDistToStepLoc) {
              minDistToStepLoc = dist;
            }
          }
        }

        // Estimate current step index relative to closest point on polyline
        const stepFraction = closestIndex / Math.max(1, geoCoords.length - 1);
        activeIdx = Math.min(steps.length - 1, Math.floor(stepFraction * steps.length));

        setCurrentStepIdx(activeIdx);

        // Distance to next maneuver
        const nextStep = steps[activeIdx + 1] || steps[activeIdx];
        if (nextStep && nextStep.location && nextStep.location.length >= 2) {
          const [nLng, nLat] = nextStep.location;
          setDistToManeuverMeters(haversineDistanceMeters(curLat, curLng, nLat, nLng));
        }
      }
    }
  }, [rescuerLocation?.lat, rescuerLocation?.lng, customDestination, aiRoute, isArrived]); // eslint-disable-line react-hooks/exhaustive-deps

  // 7. Live Telemetry Streaming
  useEffect(() => {
    if (!rescuerLocation || !selectedDispatchId) return;

    const lastLoc = lastSentLocationRef.current;
    if (lastLoc) {
      const distM = haversineDistanceMeters(rescuerLocation.lat, rescuerLocation.lng, lastLoc.lat, lastLoc.lng);
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
        }

      } catch (err) {
        console.warn('Live telemetry sync warning:', err);
      }
    }

    const interval = setInterval(sendTelemetry, GPS_UPDATE_INTERVAL_MS);
    sendTelemetry();

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [selectedDispatchId, rescuerLocation?.lat, rescuerLocation?.lng]);

  // Requirement 19: Recenter Map Action
  const handleRecenter = () => {
    refreshGps();
    if (rescuerLocation) {
      setMapCenter([rescuerLocation.lat, rescuerLocation.lng]);
      setMapZoom(16);
    }
  };

  // Requirement 9: Manual Reroute Action
  const handleManualReroute = () => {
    if (!customDestination) return;
    const rescuerLat = rescuerLocation?.lat ?? 12.973;
    const rescuerLng = rescuerLocation?.lng ?? 77.591;

    const startPt: LocationPoint = {
      lat: rescuerLat,
      lng: rescuerLng,
      name: 'Current Rescuer Live GPS',
    };

    triggerRouteCalculation(startPt, customDestination, true);
  };

  // Turn maneuver icon helper
  const renderTurnIcon = (turnType?: string) => {

    const t = (turnType || '').toLowerCase();
    if (t === 'start' || t === 'depart') return <Truck className="w-5 h-5 text-cyan-400" />;
    if (t === 'arrive') return <Target className="w-5 h-5 text-emerald-400" />;
    if (t.includes('left')) return <CornerUpLeft className="w-5 h-5 text-amber-400" />;
    if (t.includes('right')) return <CornerUpRight className="w-5 h-5 text-amber-400" />;
    if (t.includes('u_turn')) return <RefreshCw className="w-5 h-5 text-red-400" />;
    return <ArrowUp className="w-5 h-5 text-cyan-400" />;
  };

  // Build map markers for incidents
  const mapIncidents: Incident[] = incidentsList.map((inc) => {
    const lat = inc.latitude || inc.location?.lat || 12.966602;
    const lng = inc.longitude || inc.location?.lng || 77.599961;
    return {
      id: inc.id,
      incident_code: inc.incident_code || inc.code || inc.id,
      incident_type: (inc.incident_type || inc.type || 'MEDICAL').toUpperCase(),
      severity: (inc.severity || 'HIGH').toUpperCase(),
      status: (inc.status || 'ACTIVE').toUpperCase(),
      latitude: lat,
      longitude: lng,
      location_name: inc.location_name || inc.title || 'Emergency Rescue Location',
      description: inc.description || 'Active emergency rescue request.',
      code: inc.incident_code || inc.code || inc.id,
      title: inc.title || inc.location_name || inc.incident_code || 'Rescue Request',
      type: inc.incident_type || 'medical',
      location: { lat, lng, name: inc.location_name || 'Rescue Location' },
      reportedAt: inc.created_at || 'ACTIVE',
    };
  });

  const startPt: LocationPoint | null = rescuerLocation
    ? { lat: rescuerLocation.lat, lng: rescuerLocation.lng, name: 'Rescuer Live GPS' }
    : { lat: 12.973, lng: 77.591, name: 'Rescuer Base Location' };

  const destPt: LocationPoint | null = customDestination;

  // GPS Accuracy Details
  const gpsAccInfo = rescuerLocation ? getGpsAccuracyStatus(rescuerLocation.accuracy) : { label: 'LOW', badgeClass: 'bg-red-500/20 text-red-400 border-red-500/40' };

  const currentStep: RouteStepDetail | null = aiRoute?.steps?.[currentStepIdx] || null;
  const nextStep: RouteStepDetail | null = aiRoute?.steps?.[currentStepIdx + 1] || null;

  return (
    <PageContainer>
      <div className="flex-1 flex flex-col lg:flex-row h-full overflow-hidden font-sans">
        {/* LEFT PANEL: ACTIVE RESCUE NAVIGATION */}
        <div className="w-full lg:w-[420px] shrink-0 bg-[#0b0f19] border-r border-slate-800 p-4 flex flex-col justify-between overflow-y-auto select-none space-y-4">
          <div>
            {/* Header */}
            <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
              <Truck className="w-5 h-5 text-cyan-400 animate-pulse" />
              <div>
                <h2 className="font-mono font-bold text-sm tracking-wider text-slate-100 uppercase">
                  🚑 ACTIVE RESCUE NAVIGATION
                </h2>
                <p className="text-[10px] font-mono text-slate-400">
                  REAL-TIME TURN-BY-TURN EMERGENCY ROUTING
                </p>
              </div>
            </div>

            {/* REQUIREMENT 18: RESCUER GPS PANEL */}
            <div className="mt-3 p-3 rounded-lg bg-slate-900/90 border border-slate-800 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-slate-300 font-bold uppercase flex items-center space-x-1.5">
                  <Radio className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
                  <span>🚑 RESCUER GPS</span>
                </span>
                <div className="flex items-center space-x-1.5">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                      gpsStatus === 'ACTIVE'
                        ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                        : 'bg-amber-500/20 text-amber-400 border-amber-500/40 animate-pulse'
                    }`}
                  >
                    ● {gpsStatus}
                  </span>
                  {rescuerLocation && (
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${gpsAccInfo.badgeClass}`}>
                      GPS {gpsAccInfo.label} ({rescuerLocation.accuracy.toFixed(0)}m)
                    </span>
                  )}
                </div>
              </div>

              {rescuerLocation ? (
                <div className="text-xs font-mono text-slate-300 pt-1 flex items-center justify-between">
                  <span className="text-slate-400 text-[10px]">CURRENT LOCATION:</span>
                  <span className="text-cyan-300 font-bold font-mono">
                    {rescuerLocation.lat.toFixed(6)}°, {rescuerLocation.lng.toFixed(6)}°
                  </span>
                </div>
              ) : (
                <p className="text-xs font-mono text-slate-400 py-1">{gpsErrorMsg || 'Acquiring live GPS position...'}</p>
              )}
            </div>

            {/* REQUIREMENT 18: DESTINATION INCIDENT PANEL */}
            <div className="mt-3 p-3 rounded-lg bg-slate-900/90 border border-slate-800 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-slate-300 font-bold uppercase flex items-center space-x-1.5">
                  <Target className="w-3.5 h-3.5 text-red-400 animate-pulse" />
                  <span>🎯 DESTINATION</span>
                </span>
                {selectedIncident && (
                  <span
                    className={`text-[9px] font-mono px-1.5 py-0.2 rounded border font-semibold ${
                      (selectedIncident.severity || '').toUpperCase() === 'CRITICAL'
                        ? 'bg-red-500/20 text-red-300 border-red-500/40'
                        : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                    }`}
                  >
                    {selectedIncident.severity || 'HIGH'}
                  </span>
                )}
              </div>

              {customDestination ? (
                <div className="space-y-1 pt-1">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-100 font-bold truncate">
                      {selectedIncident?.incident_code || selectedIncident?.title || customDestination.name || 'Selected Rescue Incident'}
                    </span>
                  </div>
                  <div className="text-xs font-mono text-slate-300 flex items-center justify-between">
                    <span className="text-slate-400 text-[10px]">COORDINATES:</span>
                    <span className="text-red-300 font-bold">
                      {customDestination.lat.toFixed(6)}°, {customDestination.lng.toFixed(6)}°
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-xs font-mono text-slate-500 py-1">No rescue incident selected.</p>
              )}
            </div>

            {/* INCIDENT SELECTION LIST */}
            <div className="mt-3 space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-mono uppercase text-slate-400 font-bold flex items-center space-x-1">
                  <AlertTriangle className="w-3 h-3 text-amber-400" />
                  <span>SELECT RESCUE REQUEST ({incidentsList.length})</span>
                </label>
                <button
                  type="button"
                  onClick={handleRouteToNearestIncident}
                  className="px-2 py-0.5 rounded bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-[10px] font-mono flex items-center space-x-1 transition cursor-pointer"
                >
                  <Target className="w-3 h-3 text-cyan-400" />
                  <span>NEAREST</span>
                </button>
              </div>

              <div className="max-h-36 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
                {incidentsList.map((inc) => {
                  const lat = inc.latitude || inc.location?.lat || 12.966602;
                  const lng = inc.longitude || inc.location?.lng || 77.599961;
                  const curLat = rescuerLocation?.lat ?? 12.973;
                  const curLng = rescuerLocation?.lng ?? 77.591;
                  const distM = haversineDistanceMeters(curLat, curLng, lat, lng);
                  const isSelected = selectedIncidentId === inc.id;

                  return (
                    <div
                      key={inc.id}
                      onClick={() => handleSelectIncidentById(inc.id)}
                      className={`p-2 rounded border transition cursor-pointer flex items-center justify-between ${
                        isSelected
                          ? 'bg-cyan-950/70 border-cyan-500 text-cyan-200 shadow'
                          : 'bg-slate-900/80 border-slate-800 hover:border-slate-700 text-slate-300'
                      }`}
                    >
                      <div className="min-w-0 pr-2">
                        <div className="flex items-center space-x-1.5">
                          <MapPin className={`w-3.5 h-3.5 shrink-0 ${isSelected ? 'text-cyan-400' : 'text-slate-400'}`} />
                          <span className="font-mono font-bold text-xs text-slate-100 truncate">
                            {inc.title || inc.incident_code || inc.id}
                          </span>
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <span className="text-xs font-mono font-bold text-cyan-400 block">{formatDistance(distM)}</span>
                        <span className="text-[9px] font-mono text-slate-500 uppercase">{isSelected ? 'ACTIVE' : 'SELECT'}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* REQUIREMENT 20: ARRIVAL BANNER */}
            {isArrived && (
              <div className="mt-3 p-3 rounded-lg bg-emerald-950/80 border border-emerald-500 text-emerald-200 shadow-lg space-y-1">
                <div className="flex items-center space-x-2 text-emerald-400 font-mono font-bold text-sm">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 animate-bounce" />
                  <span>ARRIVED AT RESCUE LOCATION</span>
                </div>
                <p className="text-xs font-mono text-emerald-300/80 pl-7">
                  Rescuer unit is within 30m of incident destination. Turn-by-turn navigation complete.
                </p>
              </div>
            )}

            {/* REQUIREMENT 9: OFF-ROUTE / REROUTING BANNER */}
            {(isOffRoute || isRerouting) && !isArrived && (
              <div className="mt-3 p-3 rounded-lg bg-amber-950/80 border border-amber-500 text-amber-200 shadow-lg space-y-1">
                <div className="flex items-center justify-between font-mono font-bold text-xs text-amber-400">
                  <span className="flex items-center space-x-1.5">
                    <AlertTriangle className="w-4 h-4 text-amber-400 animate-pulse" />
                    <span>OFF ROUTE ({offRouteDistance.toFixed(0)}m DEVIATION)</span>
                  </span>
                  <span className="animate-pulse">REROUTING...</span>
                </div>
                <p className="text-[11px] font-mono text-amber-300/80">
                  Automatically requesting updated route to target incident from current GPS.
                </p>
              </div>
            )}

            {/* REQUIREMENT 4: NO ROUTE AVAILABLE ERROR */}
            {routeError && (
              <div className="mt-3 p-3 rounded-lg bg-red-950/60 border border-red-900/80 text-red-300 text-xs font-mono space-y-1">
                <div className="font-bold flex items-center space-x-1.5">
                  <AlertTriangle className="w-4 h-4 text-red-400" />
                  <span>NO ROUTE AVAILABLE</span>
                </div>
                <p>{routeError}</p>
              </div>
            )}

            {/* REQUIREMENT 6 & 7: TURN-BY-TURN NAVIGATION INSTRUCTION PANELS */}
            {!isArrived && aiRoute && (
              <div className="mt-3 space-y-3">
                {/* CURRENT INSTRUCTION PANEL */}
                <div className="p-3.5 rounded-lg bg-gradient-to-r from-cyan-950/60 to-slate-900 border border-cyan-500/50 shadow-md space-y-2">
                  <div className="flex items-center justify-between text-[10px] font-mono text-cyan-400 font-bold uppercase tracking-wider">
                    <span className="flex items-center space-x-1">
                      <Compass className="w-3.5 h-3.5 text-cyan-400" />
                      <span>CURRENT INSTRUCTION</span>
                    </span>
                    <span>STEP {currentStepIdx + 1} OF {aiRoute.steps?.length || 1}</span>
                  </div>

                  {currentStep ? (
                    <div className="flex items-start space-x-3 pt-1">
                      <div className="w-10 h-10 rounded-lg bg-cyan-950/90 border border-cyan-500/60 flex items-center justify-center shrink-0 shadow-inner">
                        {renderTurnIcon(currentStep.turn_type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-slate-100 leading-snug">
                          {currentStep.instruction}
                        </p>
                        <div className="flex items-center space-x-2 text-xs font-mono text-cyan-300 font-bold mt-1">
                          <span>{formatDistance(distToManeuverMeters)}</span>
                          {currentStep.road_name && currentStep.road_name !== 'Emergency Route' && (
                            <>
                              <span>•</span>
                              <span className="text-slate-400 truncate">{currentStep.road_name}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs font-mono text-slate-400">Proceed along highlighted route.</p>
                  )}
                </div>

                {/* NEXT TURN PANEL */}
                {nextStep && (
                  <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800 space-y-1.5">
                    <span className="text-[10px] font-mono text-slate-400 font-bold uppercase tracking-wider block">
                      NEXT TURN
                    </span>
                    <div className="flex items-center space-x-2 text-xs font-mono">
                      <div className="w-6 h-6 rounded bg-slate-950 border border-slate-800 flex items-center justify-center shrink-0">
                        {renderTurnIcon(nextStep.turn_type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <span className="text-slate-200 font-medium block truncate">{nextStep.instruction}</span>
                        <span className="text-[10px] text-slate-400">{formatDistance(nextStep.distance_meters)}</span>
                      </div>
                    </div>
                  </div>
                )}


                {/* METRICS & ETA SUMMARY */}
                <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800 grid grid-cols-2 gap-2 text-xs font-mono">
                  <div className="p-2 rounded bg-slate-950/60 border border-slate-800">
                    <span className="text-slate-400 text-[10px] block">DISTANCE REMAINING</span>
                    <span className="text-cyan-300 font-bold text-sm block">
                      {formatDistance(remainingDistMeters)}
                    </span>
                  </div>
                  <div className="p-2 rounded bg-slate-950/60 border border-slate-800">
                    <span className="text-slate-400 text-[10px] block">ESTIMATED ARRIVAL</span>
                    <span className="text-emerald-400 font-bold text-sm block">
                      {formatDuration(remainingDurationSecs)}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* REQUIREMENT 19 & BUTTON CONTROLS */}
            <div className="mt-4 grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={handleRecenter}
                className="py-2 px-3 rounded bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 text-xs font-mono font-bold flex items-center justify-center space-x-1.5 transition cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
                <span>RECENTER GPS</span>
              </button>

              <button
                type="button"
                onClick={handleManualReroute}
                disabled={isRouting}
                className="py-2 px-3 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-mono font-bold flex items-center justify-center space-x-1.5 transition cursor-pointer disabled:opacity-50"
              >
                {isRouting ? <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-400" /> : <Navigation className="w-3.5 h-3.5 text-cyan-400" />}
                <span>REROUTE</span>
              </button>
            </div>

            {/* Reroute Status Message */}
            {rerouteStatusMsg && (
              <div className="mt-3 p-2 rounded bg-emerald-950/30 border border-emerald-800/60 text-emerald-300 text-[11px] font-mono flex items-center space-x-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <span className="truncate">{rerouteStatusMsg}</span>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT PANEL: INTERACTIVE GIS RESCUER NAVIGATION MAP */}
        <div className="flex-1 h-full relative min-h-[400px]">
          <MapView
            center={mapCenter}
            zoom={mapZoom}
            incidents={mapIncidents}
            startLocation={startPt}
            destination={destPt}
            routeGeometry={aiRoute?.geometry || liveTelemetry?.route_geometry || null}
            onIncidentSelect={(id) => handleSelectIncidentById(id)}
          />
        </div>
      </div>
    </PageContainer>
  );
};

export default RescuerModePage;
