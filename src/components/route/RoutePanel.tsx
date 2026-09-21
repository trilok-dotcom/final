import React from 'react';
import { Navigation, AlertOctagon, ShieldAlert, Cpu, Loader2, CheckCircle2, AlertTriangle } from 'lucide-react';
import type { LocationPoint, RouteResponse } from '../../types/route';
import type { Incident } from '../../types/incident';
import { LocationSelector } from './LocationSelector';

interface RoutePanelProps {
  selectedIncident?: Incident | null;
  startLocation?: LocationPoint | null;
  destination?: LocationPoint | null;
  routeResponse?: RouteResponse | null;
  selectingMode?: 'none' | 'start' | 'destination';
  isCalculating?: boolean;
  error?: string | null;
  onSetSelectingMode?: (mode: 'none' | 'start' | 'destination') => void;
  onClearLocations?: () => void;
  onCalculateRoute?: () => void;
}

export const RoutePanel: React.FC<RoutePanelProps> = ({
  selectedIncident,
  startLocation,
  destination,
  routeResponse,
  selectingMode = 'none',
  isCalculating = false,
  error = null,
  onSetSelectingMode,
  onClearLocations,
  onCalculateRoute,
}) => {
  const canCalculate = Boolean(startLocation && destination && !isCalculating);

  return (
    <div className="w-full h-full bg-[#0b0f19] border-l border-slate-800/80 flex flex-col justify-between overflow-y-auto select-none p-4 space-y-4 font-sans">
      {/* Panel Header */}
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <Navigation className="w-4 h-4 text-cyan-400" />
            <h3 className="font-mono font-bold text-sm tracking-wider text-slate-100 uppercase">
              RESCUE ROUTE
            </h3>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
            OSRM V1
          </span>
        </div>

        {/* Section 1: Incident Selection */}
        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between text-xs font-mono uppercase text-slate-400">
            <span>INCIDENT ASSIGNMENT</span>
            <span className="text-[10px] text-slate-400">TARGET</span>
          </div>

          <div className="p-3 rounded bg-slate-900/60 border border-slate-800">
            {selectedIncident ? (
              <div className="flex items-start space-x-2.5">
                <ShieldAlert className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-slate-100">{selectedIncident.title}</span>
                    <span className="text-[9px] font-mono font-bold px-1.5 py-0.2 rounded bg-red-950 text-red-400 border border-red-800 uppercase">
                      {selectedIncident.severity}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">{selectedIncident.description}</p>
                </div>
              </div>
            ) : (
              <div className="flex items-center space-x-2 text-slate-400 text-xs py-1">
                <AlertOctagon className="w-4 h-4 text-amber-500/80 shrink-0" />
                <div>
                  <span className="font-medium text-slate-300">Status: </span>
                  <span className="text-slate-400">Awaiting incident selection</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Section 2: Location Selectors */}
        <div className="mt-4 space-y-3">
          <div className="text-xs font-mono uppercase text-slate-400">
            <span>LOCATION TARGETS</span>
          </div>

          <LocationSelector
            label="Starting Point"
            type="start"
            location={startLocation || null}
            isSelecting={selectingMode === 'start'}
            onSelectOnMap={() =>
              onSetSelectingMode && onSetSelectingMode(selectingMode === 'start' ? 'none' : 'start')
            }
          />

          <LocationSelector
            label="Destination"
            type="destination"
            location={destination || null}
            isSelecting={selectingMode === 'destination'}
            onSelectOnMap={() =>
              onSetSelectingMode && onSetSelectingMode(selectingMode === 'destination' ? 'none' : 'destination')
            }
          />

          {(startLocation || destination) && (
            <div className="flex justify-end">
              <button
                type="button"
                onClick={onClearLocations}
                className="text-[10px] font-mono text-slate-400 hover:text-slate-200 underline"
              >
                Reset Map Pins
              </button>
            </div>
          )}
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mt-4 p-3 rounded bg-red-950/30 border border-red-900/60 text-red-300 text-xs font-mono flex items-start space-x-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-red-400" />
            <div>
              <span className="font-bold text-red-200 uppercase">Routing Error: </span>
              <span>{error}</span>
            </div>
          </div>
        )}

        {/* Section 3: Route Status */}
        <div className="mt-4 p-3 rounded bg-slate-900/40 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-slate-400">ROUTE STATUS:</span>
            {routeResponse ? (
              <span className="text-emerald-400 font-bold text-[11px] flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>CALCULATED (OSRM)</span>
              </span>
            ) : isCalculating ? (
              <span className="text-cyan-400 font-semibold text-[11px] flex items-center space-x-1">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>COMPUTING ROUTE...</span>
              </span>
            ) : (
              <span className="text-amber-400/90 font-semibold text-[11px]">No route calculated</span>
            )}
          </div>
          <p className="text-[11px] text-slate-400">
            {routeResponse
              ? `Real road route calculated across ${routeResponse.steps.length} maneuvers.`
              : 'Select starting point and destination on the map to compute real road geometry.'}
          </p>
        </div>
      </div>

      {/* Primary Action Button */}
      <div className="space-y-3 pt-3 border-t border-slate-800">
        <button
          type="button"
          onClick={onCalculateRoute}
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
              <span>CALCULATING VIA OSRM...</span>
            </>
          ) : (
            <>
              <Navigation className="w-4 h-4" />
              <span>CALCULATE RESCUE ROUTE</span>
            </>
          )}
        </button>

        {/* AI & GIS Infrastructure Status */}
        <div className="pt-2 text-[10px] text-slate-400 font-mono flex items-center justify-between border-t border-slate-800/40">
          <span className="flex items-center space-x-1">
            <Cpu className="w-3 h-3 text-slate-500" />
            <span>BACKEND: FASTAPI + OSRM</span>
          </span>
          <span className="text-emerald-400">ONLINE</span>
        </div>
      </div>
    </div>
  );
};
