import { useState, useCallback, useEffect } from 'react';
import type { LocationPoint } from '../types/route';

export type MapTileMode = 'dark' | 'satellite' | 'streets';

export interface MapState {
  center: [number, number];
  zoom: number;
  tileMode: MapTileMode;
  startLocation: LocationPoint | null;
  destinationLocation: LocationPoint | null;
  selectedIncidentId: string | null;
}

// Default center: Bangalore operational area where U-Net georeferenced satellite patch is located
const DEFAULT_CENTER: [number, number] = [12.973, 77.591];
const DEFAULT_ZOOM = 13;

export function useMap() {
  const [mapState, setMapState] = useState<MapState>({
    center: DEFAULT_CENTER,
    zoom: DEFAULT_ZOOM,
    tileMode: 'dark',
    startLocation: null,
    destinationLocation: null,
    selectedIncidentId: null,
  });

  // Automatically attempt browser geolocation on mount to center dashboard on current location
  useEffect(() => {
    if (typeof window !== 'undefined' && 'geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setMapState((prev) => ({
            ...prev,
            center: [pos.coords.latitude, pos.coords.longitude],
          }));
        },
        () => {
          // Fallback to default operational center
        },
        { enableHighAccuracy: true, timeout: 5000, maximumAge: 60000 }
      );
    }
  }, []);

  const setCenter = useCallback((center: [number, number]) => {
    setMapState((prev) => ({ ...prev, center }));
  }, []);

  const setZoom = useCallback((zoom: number) => {
    setMapState((prev) => ({ ...prev, zoom }));
  }, []);

  const setTileMode = useCallback((tileMode: MapTileMode) => {
    setMapState((prev) => ({ ...prev, tileMode }));
  }, []);

  const setStartLocation = useCallback((location: LocationPoint | null) => {
    setMapState((prev) => ({ ...prev, startLocation: location }));
  }, []);

  const setDestinationLocation = useCallback((location: LocationPoint | null) => {
    setMapState((prev) => ({ ...prev, destinationLocation: location }));
  }, []);

  const setSelectedIncidentId = useCallback((incidentId: string | null) => {
    setMapState((prev) => ({ ...prev, selectedIncidentId: incidentId }));
  }, []);

  const resetMapSelection = useCallback(() => {
    setMapState((prev) => ({
      ...prev,
      startLocation: null,
      destinationLocation: null,
      selectedIncidentId: null,
    }));
  }, []);

  return {
    mapState,
    setCenter,
    setZoom,
    setTileMode,
    setStartLocation,
    setDestinationLocation,
    setSelectedIncidentId,
    resetMapSelection,
  };
}
