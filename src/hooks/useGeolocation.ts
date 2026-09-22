import { useState, useEffect, useCallback, useRef } from 'react';

export const MAX_ACCEPTABLE_GPS_ACCURACY_METERS = 100.0; // Configurable max accuracy threshold
export const GPS_UPDATE_INTERVAL_MS = 3000;              // Configurable update frequency
export const GPS_MIN_MOVEMENT_METERS = 5.0;               // Configurable distance movement threshold

export interface GPSLocation {
  lat: number;
  lng: number;
  accuracy: number;
  heading: number | null;
  speed: number | null;
  timestamp: number;
}

export type GPSStatus = 'CONNECTING' | 'ACTIVE' | 'ERROR' | 'UNSUPPORTED' | 'LOST';

export interface UseGeolocationOptions {
  enableHighAccuracy?: boolean;
  timeout?: number;
  maximumAge?: number;
  autoStart?: boolean;
}

export function useGeolocation(options: UseGeolocationOptions = {}) {
  const {
    enableHighAccuracy = true,
    timeout = 10000,
    maximumAge = 1000,
    autoStart = true,
  } = options;

  const [location, setLocation] = useState<GPSLocation | null>(null);
  const [status, setStatus] = useState<GPSStatus>('CONNECTING');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const watchIdRef = useRef<number | null>(null);
  const lastLocationRef = useRef<GPSLocation | null>(null);

  const isSupported = typeof window !== 'undefined' && 'geolocation' in navigator;

  const handlePosition = useCallback((position: GeolocationPosition) => {
    const coords = position.coords;
    const newLoc: GPSLocation = {
      lat: coords.latitude,
      lng: coords.longitude,
      accuracy: coords.accuracy,
      heading: coords.heading ?? null,
      speed: coords.speed ?? null,
      timestamp: position.timestamp,
    };

    lastLocationRef.current = newLoc;
    setLocation(newLoc);
    setStatus('ACTIVE');
    setErrorMsg(null);
    setLastUpdated(new Date(position.timestamp));
  }, []);

  const handleError = useCallback((error: GeolocationPositionError) => {
    let msg = 'Failed to acquire GPS location.';
    switch (error.code) {
      case error.PERMISSION_DENIED:
        msg = 'Location permission denied by user/browser.';
        break;
      case error.POSITION_UNAVAILABLE:
        msg = 'GPS location position is unavailable.';
        break;
      case error.TIMEOUT:
        msg = 'GPS location request timed out.';
        break;
    }
    setErrorMsg(msg);
    setStatus((prev) => (prev === 'ACTIVE' && lastLocationRef.current ? 'LOST' : 'ERROR'));
  }, []);

  const startWatch = useCallback(() => {
    if (!isSupported) {
      setStatus('UNSUPPORTED');
      setErrorMsg('Browser does not support Geolocation API.');
      return;
    }

    setStatus('CONNECTING');
    setErrorMsg(null);

    // Initial position fetch
    navigator.geolocation.getCurrentPosition(handlePosition, handleError, {
      enableHighAccuracy,
      timeout,
      maximumAge,
    });

    // Continuous watchPosition tracking
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
    }

    watchIdRef.current = navigator.geolocation.watchPosition(handlePosition, handleError, {
      enableHighAccuracy,
      timeout,
      maximumAge,
    });
  }, [isSupported, handlePosition, handleError, enableHighAccuracy, timeout, maximumAge]);

  const stopWatch = useCallback(() => {
    if (watchIdRef.current !== null && isSupported) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
  }, [isSupported]);

  const refresh = useCallback(() => {
    if (!isSupported) return;
    setStatus('CONNECTING');
    navigator.geolocation.getCurrentPosition(handlePosition, handleError, {
      enableHighAccuracy,
      timeout,
      maximumAge: 0, // Force fresh fix
    });
  }, [isSupported, handlePosition, handleError, enableHighAccuracy, timeout]);

  useEffect(() => {
    if (autoStart) {
      startWatch();
    }
    return () => {
      stopWatch();
    };
  }, [autoStart, startWatch, stopWatch]);

  const isLowAccuracy = location ? location.accuracy > MAX_ACCEPTABLE_GPS_ACCURACY_METERS : false;

  return {
    location,
    status,
    errorMsg,
    lastUpdated,
    isSupported,
    isLive: status === 'ACTIVE',
    isLowAccuracy,
    startWatch,
    stopWatch,
    refresh,
    recenter: refresh,
  };
}
