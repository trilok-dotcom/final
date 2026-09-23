import React from 'react';
import type { RescueUnit } from '../../types/rescue';
import { Shield, MapPin, Radio, AlertOctagon, Plane, Truck, Anchor, Ambulance } from 'lucide-react';

interface RescueUnitCardProps {
  unit: RescueUnit;
  onAssign?: (unit: RescueUnit) => void;
}

export const RescueUnitCard: React.FC<RescueUnitCardProps> = ({ unit }) => {
  const code = unit.unit_code || unit.unitCode || 'UNIT-01';
  const type = (unit.unit_type || unit.type || 'AMBULANCE').toString().toUpperCase();
  const statusStr = (unit.status || 'AVAILABLE').toString().toUpperCase();
  const lat = unit.latitude ?? unit.location?.lat ?? 12.9797;
  const lng = unit.longitude ?? unit.location?.lng ?? 77.5834;
  const crew = unit.crew_size || unit.crewCount || 1;

  const getStatusBadgeClass = (st: string) => {
    switch (st) {
      case 'AVAILABLE':
        return 'bg-emerald-950 text-emerald-300 border-emerald-800';
      case 'EN_ROUTE':
      case 'DISPATCHED':
        return 'bg-cyan-950 text-cyan-300 border-cyan-800';
      case 'ON_SCENE':
        return 'bg-purple-950 text-purple-300 border-purple-800';
      case 'OFFLINE':
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const getUnitIcon = (t: string) => {
    if (t.includes('HELICOPTER')) return <Plane className="w-4 h-4 text-cyan-400" />;
    if (t.includes('WATERCRAFT')) return <Anchor className="w-4 h-4 text-blue-400" />;
    if (t.includes('AMBULANCE')) return <Ambulance className="w-4 h-4 text-emerald-400" />;
    if (t.includes('FIRE') || t.includes('HEAVY') || t.includes('ATV')) return <Truck className="w-4 h-4 text-amber-400" />;
    return <Shield className="w-4 h-4 text-cyan-400" />;
  };

  return (
    <div className="bg-[#0f172a]/60 border border-slate-800 rounded-lg p-4 font-sans select-none hover:border-slate-700 transition-colors">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 rounded bg-slate-800 border border-slate-700">
            {getUnitIcon(type)}
          </div>
          <div>
            <div className="font-mono text-xs font-bold text-slate-100">{code}</div>
            <div className="text-[10px] text-slate-400 font-mono uppercase">{type}</div>
          </div>
        </div>

        <span className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded border ${getStatusBadgeClass(statusStr)}`}>
          {statusStr.replace('_', ' ')}
        </span>
      </div>

      <h4 className="font-semibold text-sm text-slate-200 mt-2.5">{unit.name}</h4>
      <p className="text-xs text-slate-400 mt-1">
        {(() => {
          if (!unit.capabilities) return unit.equipmentSummary || 'Standard tactical rescue unit.';
          let caps: string[] = [];
          if (Array.isArray(unit.capabilities)) {
            caps = unit.capabilities;
          } else if (typeof unit.capabilities === 'string') {
            try {
              const parsed = JSON.parse(unit.capabilities);
              if (Array.isArray(parsed)) caps = parsed;
              else caps = [unit.capabilities];
            } catch {
              caps = [unit.capabilities];
            }
          }
          return caps.length > 0 ? `Capabilities: ${caps.join(', ')}` : (unit.equipmentSummary || 'Standard tactical rescue unit.');
        })()}
      </p>

      <div className="mt-3 pt-2.5 border-t border-slate-800/60 grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-400">
        <div className="flex items-center space-x-1.5">
          <MapPin className="w-3.5 h-3.5 text-cyan-400" />
          <span className="truncate">
            [{lat.toFixed(3)}, {lng.toFixed(3)}]
          </span>
        </div>

        <div className="flex items-center space-x-1.5">
          <Radio className="w-3.5 h-3.5 text-slate-500" />
          <span>CREW: {crew} PERS</span>
        </div>

        <div className="flex items-center space-x-1.5 col-span-2">
          <AlertOctagon className="w-3.5 h-3.5 text-slate-500" />
          <span>ASSIGNED: {unit.current_incident_id || unit.assignedIncidentCode || 'NONE (STANDBY)'}</span>
        </div>
      </div>
    </div>
  );
};
