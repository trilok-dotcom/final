import React from 'react';
import type { Incident } from '../../types/incident';
import { ShieldAlert, MapPin, Clock, Users, ArrowRight } from 'lucide-react';

interface IncidentCardProps {
  incident: Incident;
  isSelected?: boolean;
  onSelect?: (incident: Incident) => void;
  onRouteIncident?: (incident: Incident) => void;
}

export const IncidentCard: React.FC<IncidentCardProps> = ({
  incident,
  isSelected = false,
  onSelect,
  onRouteIncident,
}) => {
  const code = incident.incident_code || incident.code || 'INC-000';
  const title = incident.location_name || incident.title || 'Emergency Incident';
  const severityStr = (incident.severity || 'LOW').toString().toUpperCase();
  const statusStr = (incident.status || 'REPORTED').toString().toUpperCase();
  const lat = incident.latitude ?? incident.location?.lat ?? 12.9716;
  const lng = incident.longitude ?? incident.location?.lng ?? 77.5946;

  const getSeverityBadgeClass = (sev: string) => {
    switch (sev) {
      case 'CRITICAL':
        return 'bg-red-500/10 text-red-400 border-red-500/30';
      case 'HIGH':
        return 'bg-orange-500/10 text-orange-400 border-orange-500/30';
      case 'MEDIUM':
      case 'MODERATE':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'LOW':
      default:
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
    }
  };

  const getStatusBadgeClass = (st: string) => {
    switch (st) {
      case 'RESOLVED':
        return 'bg-emerald-950 text-emerald-300 border-emerald-800';
      case 'ACTIVE':
      case 'IN_PROGRESS':
        return 'bg-cyan-950 text-cyan-300 border-cyan-800';
      case 'DISPATCHING':
      case 'DISPATCHED':
        return 'bg-purple-950 text-purple-300 border-purple-800';
      case 'REPORTED':
      case 'VERIFIED':
      case 'UNASSIGNED':
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  return (
    <div
      onClick={() => onSelect && onSelect(incident)}
      className={`p-4 rounded-lg border transition-all cursor-pointer font-sans ${
        isSelected
          ? 'bg-slate-900 border-cyan-500/60 ring-1 ring-cyan-500/30 shadow-lg'
          : 'bg-[#0f172a]/60 hover:bg-slate-900 border-slate-800/80 hover:border-slate-700'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-2">
          <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
            {code}
          </span>
          <span className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded border ${getSeverityBadgeClass(severityStr)}`}>
            {severityStr}
          </span>
        </div>

        <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${getStatusBadgeClass(statusStr)}`}>
          {statusStr.replace('_', ' ')}
        </span>
      </div>

      <h4 className="font-semibold text-sm text-slate-100 mt-2.5">{title}</h4>
      <p className="text-xs text-slate-400 mt-1 line-clamp-2">{incident.description || 'Emergency disaster incident.'}</p>

      <div className="mt-3 pt-2.5 border-t border-slate-800/60 grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-400">
        <div className="flex items-center space-x-1.5">
          <MapPin className="w-3.5 h-3.5 text-cyan-400" />
          <span className="truncate">
            [{lat.toFixed(3)}, {lng.toFixed(3)}]
          </span>
        </div>

        <div className="flex items-center space-x-1.5">
          <Clock className="w-3.5 h-3.5 text-slate-500" />
          <span>{incident.reportedAt || 'RECENT'}</span>
        </div>

        <div className="flex items-center space-x-1.5">
          <Users className="w-3.5 h-3.5 text-slate-500" />
          <span>{incident.assigned_unit_id ? '1 UNIT ASSIGNED' : 'DISPATCH READY'}</span>
        </div>

        <div className="flex items-center space-x-1.5">
          <ShieldAlert className="w-3.5 h-3.5 text-slate-500" />
          <span>{incident.incident_type || 'EMERGENCY'}</span>
        </div>
      </div>

      {onRouteIncident && (
        <div className="mt-3 pt-2 flex justify-end">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onRouteIncident(incident);
            }}
            className="px-3 py-1 rounded bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-xs font-mono font-medium flex items-center space-x-1.5 transition-colors"
          >
            <span>SELECT FOR ROUTING</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      )}
    </div>
  );
};
