import React from 'react';
import { Plus, Minus, Locate, Layers, Eye } from 'lucide-react';
import type { MapTileMode } from '../../hooks/useMap';

interface MapControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onLocateMe: () => void;
  tileMode: MapTileMode;
  onToggleTileMode: (mode: MapTileMode) => void;
}

export const MapControls: React.FC<MapControlsProps> = ({
  onZoomIn,
  onZoomOut,
  onLocateMe,
  tileMode,
  onToggleTileMode,
}) => {
  return (
    <div className="absolute top-4 right-4 z-[400] flex flex-col space-y-2 select-none">
      {/* Zoom In & Out */}
      <div className="bg-[#0f172a]/90 backdrop-blur border border-slate-800 rounded shadow-lg overflow-hidden flex flex-col">
        <button
          type="button"
          onClick={onZoomIn}
          className="p-2 text-slate-300 hover:text-white hover:bg-slate-800/80 transition-colors border-b border-slate-800"
          title="Zoom In"
        >
          <Plus className="w-4 h-4" />
        </button>
        <button
          type="button"
          onClick={onZoomOut}
          className="p-2 text-slate-300 hover:text-white hover:bg-slate-800/80 transition-colors"
          title="Zoom Out"
        >
          <Minus className="w-4 h-4" />
        </button>
      </div>

      {/* Locate Me */}
      <div className="bg-[#0f172a]/90 backdrop-blur border border-slate-800 rounded shadow-lg overflow-hidden">
        <button
          type="button"
          onClick={onLocateMe}
          className="p-2 text-cyan-400 hover:text-cyan-300 hover:bg-slate-800/80 transition-colors flex items-center justify-center"
          title="Locate Command Center"
        >
          <Locate className="w-4 h-4" />
        </button>
      </div>

      {/* Tile Layer Toggle */}
      <div className="bg-[#0f172a]/90 backdrop-blur border border-slate-800 rounded shadow-lg overflow-hidden p-1 flex flex-col space-y-1">
        <button
          type="button"
          onClick={() => onToggleTileMode('dark')}
          className={`px-2 py-1 text-[10px] font-mono font-medium rounded flex items-center space-x-1.5 transition-colors ${
            tileMode === 'dark'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
          title="Tactical Dark Map"
        >
          <Layers className="w-3 h-3" />
          <span>DARK GIS</span>
        </button>
        <button
          type="button"
          onClick={() => onToggleTileMode('satellite')}
          className={`px-2 py-1 text-[10px] font-mono font-medium rounded flex items-center space-x-1.5 transition-colors ${
            tileMode === 'satellite'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
          title="Satellite Imagery"
        >
          <Eye className="w-3 h-3" />
          <span>SATELLITE</span>
        </button>
      </div>
    </div>
  );
};
