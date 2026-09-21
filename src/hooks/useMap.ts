import { useState, useCallback } from 'react';
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

// Default center: Central coordinates for emergency dispatch viewport demo (e.g., Miami / Coastal region prone to storm/flood incidents)
const DEFAULT_CENTER: [number, number] = [25.7617, -80.1918];
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
