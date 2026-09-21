import React, { useState } from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { MapView } from '../components/map/MapView';
import { DirectionsPanel } from '../components/route/DirectionsPanel';
import { LocationSelector } from '../components/route/LocationSelector';
import { useMap } from '../hooks/useMap';
import { calculateRescueRoute, calculateAIRoute } from '../services/routing';
import type { LocationPoint, RouteResponse, AIRouteResponse } from '../types/route';
import type { Incident } from '../types/incident';
import {
  Navigation,
  ShieldAlert,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Truck,
  Sparkles,
} from 'lucide-react';

const MOCK_INCIDENTS_LIST: Incident[] = [
  {
    id: 'inc-1',
    incident_code: 'INC-701',
    incident_type: 'FLOOD',
    severity: 'CRITICAL',
    status: 'ACTIVE',
    latitude: 12.966602,
    longitude: 77.599961,
    location_name: 'AOI 8 Mumbai / Disaster Site',
    description: 'Structural compromise and road flooding along AI mapped area.',
    code: 'INC-701',
    title: 'Flash Flood & Bridge Collapse',
    type: 'flood',
    location: { lat: 12.966602, lng: 77.599961, name: 'AOI 8 Mumbai / Disaster Site' },
    reportedAt: '12 MIN AGO',
    affectedRadiusKm: 3.5,
    assignedUnitsCount: 4,
  },
  {
    id: 'inc-2',
    incident_code: 'INC-702',
    incident_type: 'COLLAPSED_BUILDING',
    severity: 'CRITICAL',
    status: 'DISPATCHING',
    latitude: 25.752,
    longitude: -80.21,
    location_name: 'Brickell Tower',
    description: 'Electrical fire following localized structural collapse.',
    code: 'INC-702',
    title: 'Structural Failure & Fire',
    type: 'building_collapse',
    location: { lat: 25.752, lng: -80.21, name: 'Brickell Tower' },
    reportedAt: '28 MIN AGO',
    affectedRadiusKm: 1.2,
    assignedUnitsCount: 3,
  },
];

// Preset coordinates inside AI mapped region bounds (12.960 - 12.980 N, 77.580 - 77.600 E)
const AI_PRESET_START: LocationPoint = {
  lat: 12.979766,
  lng: 77.583438,
  name: 'Emergency Station Alpha',
  address: 'AI Station North Gate',
};

const AI_PRESET_DEST: LocationPoint = {
  lat: 12.966602,
  lng: 77.599961,
  name: 'Disaster Zone Site #4',
  address: 'Sector 4 Flash Flood Area',
};

export const RoutePlanningPage: React.FC = () => {
  const {
    mapState,
    setTileMode,
    setStartLocation,
    setDestinationLocation,
    setSelectedIncidentId,
    setCenter,
  } = useMap();

  const [routingMode, setRoutingMode] = useState<'standard' | 'ai'>('ai');
  const [vehicleType, setVehicleType] = useState<string>('ambulance');
  const [selectingMode, setSelectingMode] = useState<'none' | 'start' | 'destination'>('none');
  const [routeResponse, setRouteResponse] = useState<RouteResponse | null>(null);
  const [aiRouteResponse, setAiRouteResponse] = useState<AIRouteResponse | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedIncident =
    MOCK_INCIDENTS_LIST.find((i) => i.id === mapState.selectedIncidentId) || null;
  const canCalculate = Boolean(mapState.startLocation && mapState.destinationLocation && !isCalculating);

  const handleMapClick = (point: LocationPoint) => {
    if (selectingMode === 'start') {
      setStartLocation(point);
      setSelectingMode('none');
      setRouteResponse(null);
      setAiRouteResponse(null);
      setError(null);
    } else if (selectingMode === 'destination') {
      setDestinationLocation(point);
      setSelectingMode('none');
      setRouteResponse(null);
      setAiRouteResponse(null);
      setError(null);
    }
  };

  const handleLoadAiPresets = () => {
    setStartLocation(AI_PRESET_START);
    setDestinationLocation(AI_PRESET_DEST);
    setCenter([12.973, 77.591]);
    setRouteResponse(null);
    setAiRouteResponse(null);
    setError(null);
  };

  const handleModeChange = (mode: 'standard' | 'ai') => {
    setRoutingMode(mode);
    setRouteResponse(null);
    setAiRouteResponse(null);
    setError(null);
    if (mode === 'ai' && !mapState.startLocation && !mapState.destinationLocation) {
      handleLoadAiPresets();
    }
  };

  const handleCalculateRoute = async () => {
    if (!mapState.startLocation || !mapState.destinationLocation) return;
    setIsCalculating(true);
    setError(null);
    setRouteResponse(null);
    setAiRouteResponse(null);

    try {
      if (routingMode === 'ai') {
        const result = await calculateAIRoute({
          start: mapState.startLocation,
          destination: mapState.destinationLocation,
          vehicle_type: vehicleType,
          avoid_low_confidence: true,
        });
        setAiRouteResponse(result);
      } else {
        const result = await calculateRescueRoute({
          startLocation: mapState.startLocation,
          destination: mapState.destinationLocation,
          incidentId: mapState.selectedIncidentId || undefined,
          vehicleType: vehicleType,
        });
        setRouteResponse(result);
      }
    } catch (err) {
      if (err instanceof Error) {
        let msg = err.message;
        if (msg.includes('off_road') || msg.includes('too far')) {
          msg = 'OFF ROAD: Selected location is too far from the detected AI road network.';
        } else if (msg.includes('no_path_found') || msg.includes('connected')) {
          msg = 'NO PATH: No connected AI road route exists between these locations.';
        } else if (msg.includes('out_of_bounds') || msg.includes('outside')) {
          msg = 'OUT OF BOUNDS: Selected location is outside the currently supported AI mapping area (12.960-12.980° N, 77.580-77.600° E).';
        } else if (msg.includes('fetch') || msg.includes('Network')) {
          msg = 'NETWORK ERROR: Unable to connect to the RESQROUTE routing service.';
        }
        setError(msg);
      } else {
        setError('Failed to calculate route via routing engine.');
      }
    } finally {
      setIsCalculating(false);
    }
  };

  return (
    <PageContainer>
      <div className="flex-1 flex flex-col lg:flex-row h-full overflow-hidden">
        {/* LEFT: Route Configuration Panel */}
        <div className="w-full lg:w-80 shrink-0 bg-[#0b0f19] border-r border-slate-800 p-4 flex flex-col justify-between overflow-y-auto select-none space-y-4 font-sans">
          <div>
            <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
              <Navigation className="w-4 h-4 text-cyan-400" />
              <h3 className="font-mono font-bold text-sm tracking-wider text-slate-100 uppercase">
                ROUTE CONFIGURATION
              </h3>
            </div>

            {/* ROUTING ENGINE SELECTOR MODE */}
            <div className="mt-4 space-y-1.5">
              <label className="text-xs font-mono uppercase text-slate-400 block">
                ROUTING ENGINE MODE
              </label>
              <div className="grid grid-cols-2 gap-1.5 p-1 rounded bg-slate-900 border border-slate-800">
                <button
                  type="button"
                  onClick={() => handleModeChange('ai')}
                  className={`py-1.5 px-2 rounded text-[11px] font-mono font-bold transition-all flex items-center justify-center space-x-1.5 ${
                    routingMode === 'ai'
                      ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Cpu className="w-3.5 h-3.5" />
                  <span>AI EMERGENCY</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleModeChange('standard')}
                  className={`py-1.5 px-2 rounded text-[11px] font-mono font-bold transition-all flex items-center justify-center space-x-1.5 ${
                    routingMode === 'standard'
                      ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Navigation className="w-3.5 h-3.5" />
                  <span>STANDARD OSRM</span>
                </button>
              </div>
            </div>

            {/* AI Region Shortcut Preset Button */}
            {routingMode === 'ai' && (
              <div className="mt-3">
                <button
                  type="button"
                  onClick={handleLoadAiPresets}
                  className="w-full py-1.5 px-3 rounded bg-cyan-950/40 border border-cyan-800/60 hover:bg-cyan-900/50 text-cyan-300 text-xs font-mono flex items-center justify-center space-x-2 transition-colors cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                  <span>LOAD AI REGION PRESETS</span>
                </button>
              </div>
            )}

            {/* Vehicle Type Selector */}
            <div className="mt-4 space-y-1.5">
              <label className="text-xs font-mono uppercase text-slate-400 block flex items-center justify-between">
                <span>EMERGENCY VEHICLE</span>
                <Truck className="w-3.5 h-3.5 text-slate-400" />
              </label>
              <select
                value={vehicleType}
                onChange={(e) => setVehicleType(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="ambulance">AMBULANCE (50 km/h)</option>
                <option value="fire_truck">FIRE TRUCK (40 km/h)</option>
                <option value="rescue">RESCUE UNIT (45 km/h)</option>
                <option value="police">POLICE VEHICLE (55 km/h)</option>
              </select>
            </div>

            {/* Incident Selection Dropdown */}
            <div className="mt-4 space-y-1.5">
              <label className="text-xs font-mono uppercase text-slate-400 block">
                TARGET INCIDENT
              </label>
              <select
                value={mapState.selectedIncidentId || ''}
                onChange={(e) => {
                  const incId = e.target.value || null;
                  setSelectedIncidentId(incId);
                  const inc = MOCK_INCIDENTS_LIST.find((i) => i.id === incId);
                  if (inc) {
                    const lat = inc.latitude ?? inc.location?.lat ?? 12.97;
                    const lng = inc.longitude ?? inc.location?.lng ?? 77.58;
                    const locName = inc.location_name || inc.title || 'Target Incident';
                    setDestinationLocation({ lat, lng, name: locName });
                    setCenter([lat, lng]);
                  }
                }}
                className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="">-- Select Incident --</option>
                {MOCK_INCIDENTS_LIST.map((inc) => (
                  <option key={inc.id} value={inc.id}>
                    [{inc.code}] {inc.title} ({inc.severity.toUpperCase()})
                  </option>
                ))}
              </select>
            </div>

            {/* Location Selectors */}
            <div className="mt-4 space-y-3">
              <LocationSelector
                label="START LOCATION"
                type="start"
                location={mapState.startLocation}
                isSelecting={selectingMode === 'start'}
                onSelectOnMap={() => setSelectingMode(selectingMode === 'start' ? 'none' : 'start')}
              />

              <LocationSelector
                label="DESTINATION"
                type="destination"
                location={mapState.destinationLocation}
                isSelecting={selectingMode === 'destination'}
                onSelectOnMap={() =>
                  setSelectingMode(selectingMode === 'destination' ? 'none' : 'destination')
                }
              />
            </div>

            {selectedIncident && (
              <div className="mt-4 p-3 rounded bg-red-950/20 border border-red-900/40 space-y-1">
                <div className="flex items-center space-x-1.5 text-xs font-mono text-red-400">
                  <ShieldAlert className="w-3.5 h-3.5" />
                  <span className="font-bold">{selectedIncident.code} TARGET ASSIGNED</span>
                </div>
                <p className="text-[11px] text-slate-400">{selectedIncident.description}</p>
              </div>
            )}

            {/* AI Region Coverage Notice */}
            {routingMode === 'ai' && (
              <div className="mt-4 p-2.5 rounded bg-slate-900/80 border border-slate-800 text-[11px] font-mono text-slate-400 space-y-1">
                <span className="text-cyan-400 font-bold block">AI MAP COVERAGE:</span>
                <span>Supported Bounds: 12.9600-12.9800° N, 77.5800-77.6000° E</span>
              </div>
            )}

            {/* Error Banner */}
            {error && (
              <div className="mt-4 p-3 rounded bg-red-950/40 border border-red-900/80 text-red-300 text-xs font-mono flex items-start space-x-2">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-red-400" />
                <div>
                  <span className="font-bold text-red-200 uppercase">Routing Error: </span>
                  <span>{error}</span>
                </div>
              </div>
            )}
          </div>

          {/* Calculate Button */}
          <div className="space-y-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={handleCalculateRoute}
              disabled={!canCalculate}
              className={`w-full py-2.5 px-4 rounded font-mono font-bold text-xs uppercase tracking-wider border transition-all flex items-center justify-center space-x-2 shadow-lg ${
                canCalculate
                  ? 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 border-cyan-400 cursor-pointer shadow-cyan-500/20'
                  : 'bg-slate-800 text-slate-400 border-slate-700 cursor-not-allowed opacity-60'
              }`}
            >
              {isCalculating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-slate-950" />
                  <span>
                    {routingMode === 'ai'
                      ? 'CALCULATING AI EMERGENCY ROUTE...'
                      : 'CALCULATING VIA OSRM...'}
                  </span>
                </>
              ) : (
                <>
                  {routingMode === 'ai' ? (
                    <Cpu className="w-4 h-4" />
                  ) : (
                    <Navigation className="w-4 h-4" />
                  )}
                  <span>
                    {routingMode === 'ai' ? 'CALCULATE AI ROUTE' : 'CALCULATE RESCUE ROUTE'}
                  </span>
                </>
              )}
            </button>

            {aiRouteResponse && routingMode === 'ai' && (
              <div className="text-[11px] font-mono text-emerald-400 bg-emerald-950/30 border border-emerald-900/40 p-2 rounded flex items-center space-x-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>AI ROUTE ACTIVE (U-NET + DIJKSTRA)</span>
              </div>
            )}

            {routeResponse && routingMode === 'standard' && (
              <div className="text-[11px] font-mono text-emerald-400 bg-emerald-950/30 border border-emerald-900/40 p-2 rounded flex items-center space-x-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>STANDARD ROUTE ACTIVE (OSRM)</span>
              </div>
            )}
          </div>
        </div>

        {/* CENTER: Large GIS Map */}
        <div className="flex-1 h-full relative min-h-[350px]">
          <MapView
            center={mapState.center}
            zoom={mapState.zoom}
            tileMode={mapState.tileMode}
            onTileModeChange={setTileMode}
            incidents={MOCK_INCIDENTS_LIST}
            startLocation={mapState.startLocation}
            destination={mapState.destinationLocation}
            routeGeometry={
              routingMode === 'ai'
                ? aiRouteResponse?.geometry || null
                : routeResponse?.geometry || null
            }
            onMapClick={handleMapClick}
            interactiveSelectMode={selectingMode}
          />
        </div>

        {/* RIGHT: Directions Panel */}
        <div className="w-full lg:w-80 shrink-0 h-auto lg:h-full z-10">
          <DirectionsPanel
            route={routeResponse}
            aiRoute={aiRouteResponse}
            routingMode={routingMode}
            selectedVehicle={vehicleType}
          />
        </div>
      </div>
    </PageContainer>
  );
};
