import React, { useState } from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { MapView } from '../components/map/MapView';
import { useGeolocation, MAX_ACCEPTABLE_GPS_ACCURACY_METERS } from '../hooks/useGeolocation';
import { createIncident } from '../services/incidents';
import type { Incident } from '../types/incident';
import {
  AlertTriangle,
  RefreshCw,
  ShieldAlert,
  CheckCircle2,
  Loader2,
  Radio,
} from 'lucide-react';

export const RequestRescuePage: React.FC = () => {
  const {
    location,
    status: gpsStatus,
    errorMsg,
    isLowAccuracy,
    refresh: refreshGps,
  } = useGeolocation({ autoStart: true });

  const [incidentType, setIncidentType] = useState<string>('MEDICAL');
  const [severity, setSeverity] = useState<string>('HIGH');
  const [description, setDescription] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submittedIncident, setSubmittedIncident] = useState<Incident | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  // Default fallback center in Bangalore AI region if GPS connecting/failing
  const defaultCenter: [number, number] = [12.9716, 77.5946];
  const mapCenter: [number, number] = location
    ? [location.lat, location.lng]
    : defaultCenter;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!location && gpsStatus !== 'ACTIVE') {
      setFormError('GPS location is unavailable. Please enable location permissions or retry.');
      return;
    }

    const lat = location?.lat ?? defaultCenter[0];
    const lng = location?.lng ?? defaultCenter[1];

    setIsSubmitting(true);
    try {
      const created = await createIncident({
        incident_type: incidentType,
        severity: severity,
        latitude: lat,
        longitude: lng,
        location_name: `Victim GPS Location (${lat.toFixed(4)}°, ${lng.toFixed(4)}°)`,
        description: description || `Emergency rescue request submitted via live GPS.`,
        reported_by: 'VICTIM_LIVE_GPS',
        location_source: 'GPS',
        location_accuracy: location?.accuracy || 10.0,
        timestamp: new Date().toISOString(),
      });
      setSubmittedIncident(created);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to submit rescue request.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Convert created incident to map marker array
  const mapIncidents: Incident[] = submittedIncident
    ? [submittedIncident]
    : location
    ? [
        {
          id: 'victim-live-gps',
          incident_code: 'VICTIM-GPS',
          incident_type: incidentType,
          severity: severity,
          status: 'REPORTED',
          latitude: location.lat,
          longitude: location.lng,
          location_name: 'Your Current GPS Position',
          description: 'Emergency Rescue Request Location',
          code: 'VICTIM-GPS',
          title: 'Your Location',
          type: incidentType.toLowerCase(),
          location: { lat: location.lat, lng: location.lng, name: 'Current GPS' },
          reportedAt: 'NOW',
        },
      ]
    : [];

  return (
    <PageContainer>
      <div className="flex-1 flex flex-col lg:flex-row h-full overflow-hidden font-sans">
        {/* LEFT: Incident Request Form */}
        <div className="w-full lg:w-96 shrink-0 bg-[#0b0f19] border-r border-slate-800 p-4 flex flex-col justify-between overflow-y-auto select-none space-y-4">
          <div>
            {/* Header */}
            <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
              <ShieldAlert className="w-5 h-5 text-red-500 animate-pulse" />
              <div>
                <h2 className="font-mono font-bold text-sm tracking-wider text-slate-100 uppercase">
                  🚨 REQUEST RESCUE
                </h2>
                <p className="text-[10px] font-mono text-slate-400">
                  VICTIM / PUBLIC EMERGENCY PORTAL
                </p>
              </div>
            </div>

            {/* GPS Status Badge & Live Metrics */}
            <div className="mt-4 p-3 rounded-lg bg-slate-900/90 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
                  <Radio className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
                  <span>GPS TELEMETRY STATUS</span>
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

              {location ? (
                <div className="space-y-1 text-xs font-mono text-slate-300 pt-1 border-t border-slate-800/60">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Latitude:</span>
                    <span className="text-cyan-300 font-bold">{location.lat.toFixed(6)}°</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Longitude:</span>
                    <span className="text-cyan-300 font-bold">{location.lng.toFixed(6)}°</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Accuracy:</span>
                    <span
                      className={`font-bold ${
                        isLowAccuracy ? 'text-amber-400' : 'text-emerald-400'
                      }`}
                    >
                      {location.accuracy.toFixed(1)} meters
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-xs font-mono text-slate-400 py-1">
                  {errorMsg || 'Detecting live GPS coordinates from browser...'}
                </p>
              )}

              {isLowAccuracy && (
                <div className="p-2 rounded bg-amber-950/40 border border-amber-800/60 text-[11px] font-mono text-amber-300 flex items-center space-x-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-amber-400" />
                  <span>⚠ LOW GPS ACCURACY (&gt; {MAX_ACCEPTABLE_GPS_ACCURACY_METERS}m)</span>
                </div>
              )}

              <button
                type="button"
                onClick={refreshGps}
                className="w-full py-1.5 px-3 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-mono flex items-center justify-center space-x-1.5 transition-colors cursor-pointer mt-2"
              >
                <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
                <span>RECENTER / REFRESH GPS</span>
              </button>
            </div>

            {/* Submission Confirmation Card */}
            {submittedIncident ? (
              <div className="mt-4 p-4 rounded-lg bg-emerald-950/30 border border-emerald-800/80 space-y-3">
                <div className="flex items-center space-x-2 text-emerald-400">
                  <CheckCircle2 className="w-5 h-5" />
                  <span className="font-mono font-bold text-sm tracking-wider uppercase">
                    RESCUE REQUEST SUBMITTED
                  </span>
                </div>
                <div className="space-y-1 text-xs font-mono text-slate-300">
                  <div className="flex justify-between border-b border-emerald-900/60 pb-1">
                    <span className="text-slate-400">INCIDENT CODE:</span>
                    <span className="font-bold text-emerald-300">{submittedIncident.incident_code}</span>
                  </div>
                  <div className="flex justify-between border-b border-emerald-900/60 pb-1">
                    <span className="text-slate-400">INCIDENT TYPE:</span>
                    <span className="font-bold text-slate-100">{submittedIncident.incident_type}</span>
                  </div>
                  <div className="flex justify-between border-b border-emerald-900/60 pb-1">
                    <span className="text-slate-400">LOCATION STATUS:</span>
                    <span className="font-bold text-cyan-300">FIXED DESTINATION</span>
                  </div>
                  <div className="flex justify-between pt-1">
                    <span className="text-slate-400">STATUS:</span>
                    <span className="font-bold text-amber-400 animate-pulse">
                      {submittedIncident.status} — DISPATCHING UNIT
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setSubmittedIncident(null)}
                  className="w-full py-2 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-mono font-bold transition-colors cursor-pointer mt-2"
                >
                  SUBMIT NEW RESCUE REQUEST
                </button>
              </div>
            ) : (
              /* Request Form */
              <form onSubmit={handleSubmit} className="mt-4 space-y-4">
                {/* Incident Type */}
                <div className="space-y-1.5">
                  <label className="text-xs font-mono uppercase text-slate-400 block">
                    EMERGENCY INCIDENT TYPE
                  </label>
                  <select
                    value={incidentType}
                    onChange={(e) => setIncidentType(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-red-500"
                  >
                    <option value="MEDICAL">🚑 MEDICAL EMERGENCY</option>
                    <option value="FIRE">🔥 STRUCTURAL / VEHICLE FIRE</option>
                    <option value="ACCIDENT">💥 VEHICLE ACCIDENT / COLLISION</option>
                    <option value="FLOOD">🌊 FLASH FLOOD / INUNDATION</option>
                    <option value="COLLAPSED_BUILDING">🏢 COLLAPSED BUILDING / TRAPPED</option>
                    <option value="EARTHQUAKE">🌋 EARTHQUAKE / DISASTER</option>
                    <option value="OTHER">⚠️ OTHER EMERGENCY</option>
                  </select>
                </div>

                {/* Severity */}
                <div className="space-y-1.5">
                  <label className="text-xs font-mono uppercase text-slate-400 block">
                    SEVERITY LEVEL
                  </label>
                  <div className="grid grid-cols-4 gap-1.5">
                    {['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map((sev) => (
                      <button
                        key={sev}
                        type="button"
                        onClick={() => setSeverity(sev)}
                        className={`py-1.5 text-[11px] font-mono font-bold rounded border transition-all ${
                          severity === sev
                            ? sev === 'CRITICAL'
                              ? 'bg-red-500 text-slate-950 border-red-400 shadow-md shadow-red-500/30'
                              : 'bg-amber-500 text-slate-950 border-amber-400'
                            : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
                        }`}
                      >
                        {sev}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Description */}
                <div className="space-y-1.5">
                  <label className="text-xs font-mono uppercase text-slate-400 block">
                    SITUATION DETAILS / DESCRIPTION
                  </label>
                  <textarea
                    rows={3}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Describe immediate danger, injuries, trapped individuals..."
                    className="w-full bg-slate-900 border border-slate-800 rounded p-2.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-red-500 resize-none"
                  />
                </div>

                {formError && (
                  <div className="p-3 rounded bg-red-950/40 border border-red-900/80 text-red-300 text-xs font-mono flex items-start space-x-2">
                    <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-red-400" />
                    <span>{formError}</span>
                  </div>
                )}

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className={`w-full py-3 px-4 rounded font-mono font-bold text-xs uppercase tracking-wider border transition-all flex items-center justify-center space-x-2 shadow-lg ${
                    !isSubmitting
                      ? 'bg-red-600 hover:bg-red-500 text-white border-red-500 cursor-pointer shadow-red-600/30'
                      : 'bg-slate-800 text-slate-500 border-slate-700 cursor-not-allowed'
                  }`}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin text-white" />
                      <span>SUBMITTING EMERGENCY REQUEST...</span>
                    </>
                  ) : (
                    <>
                      <ShieldAlert className="w-4 h-4 text-white" />
                      <span>🚨 REQUEST IMMEDIATE RESCUE</span>
                    </>
                  )}
                </button>
              </form>
            )}
          </div>
        </div>

        {/* RIGHT: Live GIS Map View */}
        <div className="flex-1 h-full relative min-h-[400px]">
          <MapView
            center={mapCenter}
            zoom={15}
            incidents={mapIncidents}
          />
        </div>
      </div>
    </PageContainer>
  );
};
