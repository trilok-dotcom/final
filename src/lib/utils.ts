import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDistance(meters: number): string {
  if (meters >= 1000) {
    return `${(meters / 1000).toFixed(1)} km`;
  }
  return `${Math.round(meters)} m`;
}

export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  if (mins >= 60) {
    const hours = Math.floor(mins / 60);
    const remMins = mins % 60;
    return `${hours}h ${remMins}m`;
  }
  return `${mins} min`;
}

/**
 * Explicit conversion function: OSRM/GeoJSON [lng, lat] -> Leaflet [lat, lng]
 */
export function geoJsonToLeafletCoordinates(coords: [number, number][]): [number, number][] {
  return coords.map(([lng, lat]) => [lat, lng]);
}

/**
 * Haversine distance between two geographic coordinates in meters.
 */
export function haversineDistanceMeters(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371000;
  const dLat = (lat2 - lat1) * (Math.PI / 180);
  const dLon = (lon2 - lon1) * (Math.PI / 180);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * (Math.PI / 180)) *
      Math.cos(lat2 * (Math.PI / 180)) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Find closest distance in meters from a GPS position to a polyline of GeoJSON [lng, lat] coordinates.
 */
export function distanceToPolylineMeters(
  currentLat: number,
  currentLng: number,
  geoJsonCoordinates: [number, number][]
): { minDistanceMeters: number; closestIndex: number; remainingDistanceMeters: number } {
  if (!geoJsonCoordinates || geoJsonCoordinates.length === 0) {
    return { minDistanceMeters: Infinity, closestIndex: 0, remainingDistanceMeters: 0 };
  }

  let minDistanceMeters = Infinity;
  let closestIndex = 0;

  for (let i = 0; i < geoJsonCoordinates.length; i++) {
    const [lng, lat] = geoJsonCoordinates[i];
    const dist = haversineDistanceMeters(currentLat, currentLng, lat, lng);
    if (dist < minDistanceMeters) {
      minDistanceMeters = dist;
      closestIndex = i;
    }
  }

  // Calculate remaining distance along polyline from closestIndex to end
  let remainingDistanceMeters = 0;
  for (let i = closestIndex; i < geoJsonCoordinates.length - 1; i++) {
    const [lng1, lat1] = geoJsonCoordinates[i];
    const [lng2, lat2] = geoJsonCoordinates[i + 1];
    remainingDistanceMeters += haversineDistanceMeters(lat1, lng1, lat2, lng2);
  }

  return { minDistanceMeters, closestIndex, remainingDistanceMeters };
}

/**
 * GPS Accuracy Evaluator
 * <= 30m GOOD
 * 30m - 100m FAIR
 * > 100m LOW
 */
export function getGpsAccuracyStatus(accuracyMeters: number): {
  label: 'GOOD' | 'FAIR' | 'LOW';
  badgeClass: string;
} {
  if (accuracyMeters <= 30) {
    return { label: 'GOOD', badgeClass: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40' };
  } else if (accuracyMeters <= 100) {
    return { label: 'FAIR', badgeClass: 'bg-amber-500/20 text-amber-400 border-amber-500/40' };
  } else {
    return { label: 'LOW', badgeClass: 'bg-red-500/20 text-red-400 border-red-500/40' };
  }
}

