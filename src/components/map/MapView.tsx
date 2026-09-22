import React, { useEffect } from 'react';
import { 
  MapContainer, 
  TileLayer, 
  Marker, 
  Popup, 
  Polyline,
  useMapEvents, 
  useMap as useReactLeafletMap 
} from 'react-leaflet';
import L from 'leaflet';
import type { LocationPoint, RouteGeometry } from '../../types/route';
import type { Incident } from '../../types/incident';
import type { RescueUnit } from '../../types/rescue';
import type { MapTileMode } from '../../hooks/useMap';
import { MapControls } from './MapControls';
import { 
  createIncidentMarkerIcon, 
  createRescueUnitMarkerIcon, 
  createLocationPinIcon 
} from './MapMarker';

interface MapViewProps {
  startLocation?: LocationPoint | null;
  destination?: LocationPoint | null;
  routeGeometry?: RouteGeometry | null;
  alternativeRouteGeometry?: RouteGeometry | null;
  incidents?: Incident[];
  rescueUnits?: RescueUnit[];
  roadOverlayUrl?: string | null;
  center?: [number, number];
  zoom?: number;
  tileMode?: MapTileMode;
  onTileModeChange?: (mode: MapTileMode) => void;
  onMapClick?: (point: LocationPoint) => void;
  onIncidentSelect?: (incidentId: string) => void;
  onRescueUnitSelect?: (unitId: string) => void;
  interactiveSelectMode?: 'none' | 'start' | 'destination';
}

// Helper component to handle auto-fit, resize, & click listeners
const MapController: React.FC<{
  center?: [number, number];
  zoom?: number;
  startLocation?: LocationPoint | null;
  destination?: LocationPoint | null;
  routeGeometry?: RouteGeometry | null;
  onMapClick?: (point: LocationPoint) => void;
}> = ({ center, zoom, startLocation, destination, routeGeometry, onMapClick }) => {
  const map = useReactLeafletMap();

  useEffect(() => {
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 100);

    const handleResize = () => {
      map.invalidateSize();
    };

    window.addEventListener('resize', handleResize);

    return () => {
      clearTimeout(timer);
      window.removeEventListener('resize', handleResize);
    };
  }, [map]);

  // Center pan update
  useEffect(() => {
    if (center) {
      map.setView(center, zoom || map.getZoom());
    }
  }, [center, zoom, map]);

  // Fit bounds when route geometry is available
  useEffect(() => {
    if (routeGeometry && routeGeometry.coordinates && routeGeometry.coordinates.length > 0) {
      // GeoJSON is [lng, lat], convert to Leaflet [lat, lng]
      const leafletCoords: [number, number][] = routeGeometry.coordinates.map(
        ([lng, lat]) => [lat, lng]
      );
      const polylineBounds = L.latLngBounds(leafletCoords);
      map.fitBounds(polylineBounds, { padding: [50, 50] });
    } else if (startLocation && destination) {
      const bounds = L.latLngBounds(
        [startLocation.lat, startLocation.lng],
        [destination.lat, destination.lng]
      );
      map.fitBounds(bounds, { padding: [60, 60], maxZoom: 15 });
    } else if (startLocation) {
      map.panTo([startLocation.lat, startLocation.lng]);
    } else if (destination) {
      map.panTo([destination.lat, destination.lng]);
    }
  }, [startLocation, destination, routeGeometry, map]);

  useMapEvents({
    click(e) {
      if (onMapClick) {
        onMapClick({
          lat: e.latlng.lat,
          lng: e.latlng.lng,
          name: `LAT ${e.latlng.lat.toFixed(4)}, LNG ${e.latlng.lng.toFixed(4)}`,
        });
      }
    },
  });

  return null;
};

export const MapView: React.FC<MapViewProps> = ({
  startLocation,
  destination,
  routeGeometry,
  alternativeRouteGeometry,
  incidents = [],
  rescueUnits = [],
  roadOverlayUrl: _roadOverlayUrl,
  center = [12.973, 77.591], // Default map center (AI georeferenced region)
  zoom = 13,
  tileMode = 'dark',
  onTileModeChange,
  onMapClick,
  onIncidentSelect,
  onRescueUnitSelect,
  interactiveSelectMode = 'none',
}) => {
  const getTileConfig = (mode: MapTileMode) => {
    switch (mode) {
      case 'satellite':
        return {
          url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
          attribution: 'Esri, Maxar, Earthstar Geographics, and the GIS User Community',
        };
      case 'streets':
        return {
          url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        };
      case 'dark':
      default:
        return {
          url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        };
    }
  };

  const activeTile = getTileConfig(tileMode);

  // Convert GeoJSON route geometry [lng, lat] to Leaflet polyline coords [lat, lng]
  const leafletPolylineCoords: [number, number][] =
    routeGeometry && routeGeometry.coordinates
      ? routeGeometry.coordinates.map(([lng, lat]) => [lat, lng])
      : [];

  // Convert GeoJSON alternative route geometry [lng, lat] to Leaflet polyline coords [lat, lng]
  const leafletAltPolylineCoords: [number, number][] =
    alternativeRouteGeometry && alternativeRouteGeometry.coordinates
      ? alternativeRouteGeometry.coordinates.map(([lng, lat]) => [lat, lng])
      : [];

  return (
    <div className="w-full h-full relative overflow-hidden bg-slate-950">
      {/* Map Control Toolbar */}
      {onTileModeChange && (
        <MapControls
          tileMode={tileMode}
          onToggleTileMode={onTileModeChange}
          onZoomIn={() => {}}
          onZoomOut={() => {}}
          onLocateMe={() => {}}
        />
      )}

      {/* Interactive Location Selection Mode Banner */}
      {interactiveSelectMode !== 'none' && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] bg-cyan-950/90 border border-cyan-500/80 text-cyan-200 px-4 py-2 rounded-full font-mono text-xs font-bold shadow-2xl flex items-center space-x-2 animate-pulse">
          <div className="w-2.5 h-2.5 rounded-full bg-cyan-400"></div>
          <span>
            CLICK MAP TO SELECT {interactiveSelectMode.toUpperCase()} LOCATION
          </span>
        </div>
      )}

      <MapContainer
        center={center}
        zoom={zoom}
        zoomControl={false}
        className="w-full h-full z-0 cursor-crosshair"
        style={{ background: '#090d16' }}
      >
        <MapController 
          center={center} 
          zoom={zoom} 
          startLocation={startLocation}
          destination={destination}
          routeGeometry={routeGeometry}
          onMapClick={onMapClick} 
        />

        <TileLayer
          url={activeTile.url}
          attribution={activeTile.attribution}
          maxZoom={19}
        />

        {/* Candidate AI Alternative Route (Dashed Amber Line) */}
        {leafletAltPolylineCoords.length > 0 && (
          <Polyline
            positions={leafletAltPolylineCoords}
            pathOptions={{
              color: '#f59e0b',
              weight: 5,
              opacity: 0.85,
              dashArray: '8, 12',
              lineCap: 'round',
              lineJoin: 'round',
            }}
          />
        )}

        {/* Real Polyline Geometry */}
        {leafletPolylineCoords.length > 0 && (
          <>
            {/* Outer Glow Line */}
            <Polyline
              positions={leafletPolylineCoords}
              pathOptions={{
                color: '#06b6d4',
                weight: 8,
                opacity: 0.4,
                lineCap: 'round',
                lineJoin: 'round',
              }}
            />
            {/* Inner Core Solid Line */}
            <Polyline
              positions={leafletPolylineCoords}
              pathOptions={{
                color: '#22d3ee',
                weight: 4,
                opacity: 0.95,
                lineCap: 'round',
                lineJoin: 'round',
              }}
            />
          </>
        )}

        {/* Incident GIS Markers */}
        {incidents.map((incident) => {
          const lat = incident.latitude ?? incident.location?.lat ?? 12.9716;
          const lng = incident.longitude ?? incident.location?.lng ?? 77.5946;
          const code = incident.incident_code || incident.code || 'INC-000';
          const title = incident.location_name || incident.title || 'Emergency Incident';
          const severity = (incident.severity || 'HIGH').toString();
          const status = (incident.status || 'ACTIVE').toString();

          return (
            <Marker
              key={incident.id}
              position={[lat, lng]}
              icon={createIncidentMarkerIcon(severity, title)}
              eventHandlers={{
                click: () => onIncidentSelect && onIncidentSelect(incident.id),
              }}
            >
              <Popup className="custom-popup">
                <div className="p-1.5 font-sans min-w-[200px]">
                  <div className="flex items-center justify-between space-x-1.5 mb-1">
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-bold border border-slate-700">
                      {code}
                    </span>
                    <span className="text-[10px] uppercase font-bold text-red-400 font-mono">
                      {severity}
                    </span>
                  </div>
                  <h4 className="font-semibold text-xs text-slate-100">{title}</h4>
                  <p className="text-[11px] text-slate-400 mt-1">{incident.description || 'Emergency incident active.'}</p>
                  <div className="mt-2 pt-1 border-t border-slate-800 flex items-center justify-between text-[10px] text-slate-400 font-mono">
                    <span>STATUS: <strong className="text-emerald-400 uppercase">{status}</strong></span>
                    <span>[{lat.toFixed(4)}, {lng.toFixed(4)}]</span>
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* Rescue Unit Markers */}
        {rescueUnits.map((unit) => {
          const lat = unit.latitude ?? unit.location?.lat ?? 12.9797;
          const lng = unit.longitude ?? unit.location?.lng ?? 77.5834;
          const code = unit.unit_code || unit.unitCode || 'UNIT-01';
          const type = unit.unit_type || unit.type || 'AMBULANCE';
          const status = unit.status || 'AVAILABLE';

          return (
            <Marker
              key={unit.id}
              position={[lat, lng]}
              icon={createRescueUnitMarkerIcon(code, type, status, unit.heading_degrees || 0)}
              eventHandlers={{
                click: () => onRescueUnitSelect && onRescueUnitSelect(unit.id),
              }}
            >
              <Popup className="custom-popup">
                <div className="p-1.5 font-sans min-w-[200px]">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-xs font-bold text-cyan-400">{code}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 uppercase font-mono">
                      {status}
                    </span>
                  </div>
                  <h4 className="font-semibold text-xs text-slate-100">{unit.name}</h4>
                  <div className="text-[11px] text-slate-400 mt-1 space-y-0.5">
                    <div>TYPE: <strong className="text-slate-200">{type}</strong></div>
                    <div>CREW: <strong className="text-slate-200">{unit.crew_size || unit.crewCount || 1} Personnel</strong></div>
                    {unit.capabilities && unit.capabilities.length > 0 && (
                      <div className="text-[10px] font-mono text-cyan-300/80">
                        {unit.capabilities.join(', ')}
                      </div>
                    )}
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* Selected Start Location Marker */}
        {startLocation && (
          <Marker
            position={[startLocation.lat, startLocation.lng]}
            icon={createLocationPinIcon('start')}
          >
            <Popup>
              <div className="p-1 font-mono text-xs">
                <div className="font-bold text-emerald-400">START LOCATION (POINT A)</div>
                <div className="text-slate-300 text-[11px] mt-1">
                  [{startLocation.lat.toFixed(4)}, {startLocation.lng.toFixed(4)}]
                </div>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Selected Destination Marker */}
        {destination && (
          <Marker
            position={[destination.lat, destination.lng]}
            icon={createLocationPinIcon('destination')}
          >
            <Popup>
              <div className="p-1 font-mono text-xs">
                <div className="font-bold text-purple-400 font-sans uppercase">Disaster Destination (Point B)</div>
                <div className="text-slate-300 text-[11px] mt-1 font-mono">
                  [{destination.lat.toFixed(4)}, {destination.lng.toFixed(4)}]
                </div>
              </div>
            </Popup>
          </Marker>
        )}
      </MapContainer>
    </div>
  );
};
