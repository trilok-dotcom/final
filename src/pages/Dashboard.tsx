import React, { useState, useEffect } from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { MapView } from '../components/map/MapView';
import { RoutePanel } from '../components/route/RoutePanel';
import { RouteSummary } from '../components/route/RouteSummary';
import { IncidentStats } from '../components/incidents/IncidentStats';
import { useMap } from '../hooks/useMap';
import { calculateRescueRoute } from '../services/routing';
import { getIncidents } from '../services/incidents';
import { getRescueUnits } from '../services/rescueUnits';
import type { Incident } from '../types/incident';
import type { RescueUnit } from '../types/rescue';
import type { LocationPoint, RouteResponse } from '../types/route';

export const DashboardPage: React.FC = () => {
  const { mapState, setTileMode, setStartLocation, setDestinationLocation, setSelectedIncidentId } = useMap();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [rescueUnits, setRescueUnits] = useState<RescueUnit[]>([]);
  const [selectingMode, setSelectingMode] = useState<'none' | 'start' | 'destination'>('none');
  const [routeResponse, setRouteResponse] = useState<RouteResponse | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadLiveMapData = async () => {
      try {
        const [incData, unitData] = await Promise.all([
          getIncidents(),
          getRescueUnits(),
        ]);
        setIncidents(incData);
        setRescueUnits(unitData);
      } catch {
        // Fallback
      }
    };
    loadLiveMapData();
    const interval = setInterval(loadLiveMapData, 3000);
    return () => clearInterval(interval);
  }, []);

  const selectedIncident = incidents.find((i) => i.id === mapState.selectedIncidentId) || null;

  const handleMapClick = (point: LocationPoint) => {
    if (selectingMode === 'start') {
      setStartLocation(point);
      setSelectingMode('none');
      setRouteResponse(null);
      setError(null);
    } else if (selectingMode === 'destination') {
      setDestinationLocation(point);
      setSelectingMode('none');
      setRouteResponse(null);
      setError(null);
    }
  };

  const handleClearLocations = () => {
    setStartLocation(null);
    setDestinationLocation(null);
    setSelectingMode('none');
    setRouteResponse(null);
    setError(null);
  };

  const handleCalculateRoute = async () => {
    if (!mapState.startLocation || !mapState.destinationLocation) return;
    setIsCalculating(true);
    setError(null);

    try {
      const result = await calculateRescueRoute({
        startLocation: mapState.startLocation,
        destination: mapState.destinationLocation,
        incidentId: mapState.selectedIncidentId || undefined,
      });
      setRouteResponse(result);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to calculate route via backend engine.');
      }
      setRouteResponse(null);
    } finally {
      setIsCalculating(false);
    }
  };

  return (
    <PageContainer>
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Main Grid Viewport: Map (Center) & Route Panel (Right) */}
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden relative">
          {/* Map Center Viewport */}
          <div className="flex-1 flex flex-col relative h-full min-h-[350px]">
            {/* Top Overlay Stats Banner */}
            <div className="absolute top-4 left-4 z-[400] max-w-xl hidden sm:block">
              <IncidentStats />
            </div>

            <MapView
              center={mapState.center}
              zoom={mapState.zoom}
              tileMode={mapState.tileMode}
              onTileModeChange={setTileMode}
              incidents={incidents}
              rescueUnits={rescueUnits}
              startLocation={mapState.startLocation}
              destination={mapState.destinationLocation}
              routeGeometry={routeResponse?.geometry || null}
              onMapClick={handleMapClick}
              onIncidentSelect={(id) => setSelectedIncidentId(id)}
              interactiveSelectMode={selectingMode}
            />
          </div>

          {/* Right Information Panel */}
          <div className="w-full lg:w-96 shrink-0 h-auto lg:h-full z-10 border-t lg:border-t-0 border-slate-800">
            <RoutePanel
              selectedIncident={selectedIncident}
              startLocation={mapState.startLocation}
              destination={mapState.destinationLocation}
              routeResponse={routeResponse}
              selectingMode={selectingMode}
              isCalculating={isCalculating}
              error={error}
              onSetSelectingMode={(mode) => setSelectingMode(mode)}
              onClearLocations={handleClearLocations}
              onCalculateRoute={handleCalculateRoute}
            />
          </div>
        </div>

        {/* Bottom Route Summary Banner */}
        <RouteSummary route={routeResponse} />
      </div>
    </PageContainer>
  );
};
