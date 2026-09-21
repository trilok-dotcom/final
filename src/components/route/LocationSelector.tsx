import React from 'react';
import { Crosshair, CheckCircle2 } from 'lucide-react';
import type { LocationPoint } from '../../types/route';

interface LocationSelectorProps {
  label: string;
  type: 'start' | 'destination';
  location: LocationPoint | null;
  onSelectOnMap?: () => void;
  isSelecting?: boolean;
}

export const LocationSelector: React.FC<LocationSelectorProps> = ({
  label,
  type,
  location,
  onSelectOnMap,
  isSelecting = false,
}) => {
  const isStart = type === 'start';
  const buttonText = isSelecting
    ? 'CLICK MAP...'
    : location
    ? 'CHANGE'
    : isStart
    ? 'SET START'
    : 'SET DESTINATION';

  return (
    <div className="space-y-1.5 font-sans">
      <div className="flex items-center justify-between text-xs font-medium">
        <span className="uppercase tracking-wider font-mono text-[11px] text-slate-400">
          {label}
        </span>
        {location && (
          <span className="text-[10px] font-mono text-cyan-400 font-semibold flex items-center space-x-1">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            <span>[{location.lat.toFixed(4)}, {location.lng.toFixed(4)}]</span>
          </span>
        )}
      </div>

      <div
        className={`p-3 rounded border transition-all ${
          isSelecting
            ? 'bg-cyan-950/40 border-cyan-400 ring-2 ring-cyan-500/40 shadow-lg'
            : location
            ? 'bg-slate-900/90 border-slate-700/90'
            : 'bg-slate-900/40 border-slate-800'
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2.5 overflow-hidden">
            <div
              className={`w-7 h-7 rounded flex items-center justify-center shrink-0 border ${
                isStart
                  ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400 font-bold font-mono text-xs'
                  : 'bg-purple-500/10 border-purple-500/40 text-purple-400 font-bold font-mono text-xs'
              }`}
            >
              {isStart ? 'A' : 'B'}
            </div>
            <div className="truncate">
              <div className="text-xs font-semibold text-slate-100 truncate">
                {location
                  ? location.name || `${location.lat.toFixed(4)}, ${location.lng.toFixed(4)}`
                  : isStart
                  ? 'Select Rescue Start Location'
                  : 'Select Disaster Destination'}
              </div>
              <p className="text-[10px] text-slate-400 font-mono truncate">
                {location
                  ? `LAT: ${location.lat.toFixed(4)} | LNG: ${location.lng.toFixed(4)}`
                  : isSelecting
                  ? 'Click any point on the GIS map canvas'
                  : 'No coordinates specified'}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onSelectOnMap}
            className={`p-2 rounded text-xs font-mono font-bold flex items-center space-x-1.5 border transition-all shrink-0 ${
              isSelecting
                ? 'bg-cyan-400 text-slate-950 border-cyan-300 shadow-md animate-pulse'
                : location
                ? 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700'
                : 'bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border-cyan-500/30'
            }`}
            title={`Click to set ${label.toLowerCase()} on interactive map`}
          >
            <Crosshair className="w-3.5 h-3.5" />
            <span className="text-[10px] uppercase">{buttonText}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
