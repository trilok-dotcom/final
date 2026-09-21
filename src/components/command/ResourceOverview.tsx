import React from 'react';
import { Shield, Truck, Ambulance, Flame } from 'lucide-react';
import type { ResourceGroupSummary } from '../../types/commandCenter';

interface ResourceOverviewProps {
  resources: ResourceGroupSummary[];
}

export const ResourceOverview: React.FC<ResourceOverviewProps> = ({ resources }) => {
  const getUnitTypeIcon = (type: string) => {
    switch (type.toUpperCase()) {
      case 'AMBULANCE':
      case 'MEDICAL':
        return <Ambulance className="w-4 h-4 text-emerald-400" />;
      case 'FIRE_TRUCK':
      case 'FIRE':
        return <Flame className="w-4 h-4 text-amber-400" />;
      case 'RESCUE_TEAM':
      case 'HAZMAT':
      default:
        return <Truck className="w-4 h-4 text-blue-400" />;
    }
  };

  return (
    <div className="bg-slate-900/80 backdrop-blur border border-slate-800 rounded-xl p-4 flex flex-col h-full shadow-lg">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-emerald-400" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
            Rescue Resource Availability (Stage 7A / 8B)
          </h2>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {resources.length === 0 ? (
          <div className="col-span-full text-center py-6 text-slate-500 text-xs">
            No rescue unit data registered in database.
          </div>
        ) : (
          resources.map((group) => {
            const availablePct = group.total > 0 ? Math.round((group.available / group.total) * 100) : 0;

            return (
              <div
                key={group.unit_type}
                className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 hover:border-slate-700 transition"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {getUnitTypeIcon(group.unit_type)}
                    <span className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
                      {group.unit_type.replace('_', ' ')}
                    </span>
                  </div>
                  <span className="text-xs font-mono font-bold text-slate-300">
                    {group.available}/{group.total}
                  </span>
                </div>

                {/* Progress bar */}
                <div className="mt-2.5 w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                    style={{ width: `${availablePct}%` }}
                  />
                </div>

                <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                  <span className="text-emerald-400">{group.available} Ready</span>
                  <span className="text-blue-400">{group.dispatched} Busy</span>
                  {group.maintenance > 0 && <span className="text-slate-500">{group.maintenance} Maint</span>}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
