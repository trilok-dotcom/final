import React from 'react';
import { ShieldAlert, Bell, MapPin, UserCheck, Activity } from 'lucide-react';

interface TopBarProps {
  onToggleSidebar?: () => void;
}

export const TopBar: React.FC<TopBarProps> = () => {
  return (
    <header className="h-14 bg-[#0b0f19] border-b border-slate-800/80 px-4 flex items-center justify-between shrink-0 select-none z-20">
      {/* Left section: Brand & Command Center title */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 rounded bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold tracking-wider text-sm text-slate-100 uppercase font-mono">
                RESQROUTE
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/60 font-mono">
                GIS v1.0
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">
              Emergency Response Command Center
            </p>
          </div>
        </div>

        <div className="h-5 w-px bg-slate-800 mx-2 hidden sm:block" />

        {/* Status Indicator */}
        <div className="hidden sm:flex items-center space-x-2 bg-emerald-950/40 border border-emerald-800/50 px-2.5 py-1 rounded text-xs font-mono text-emerald-400">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="font-semibold tracking-wide text-[11px]">SYSTEM OPERATIONAL</span>
        </div>
      </div>

      {/* Right section: System details, notifications, profile placeholder */}
      <div className="flex items-center space-x-4">
        {/* Telemetry / Location badge */}
        <div className="hidden md:flex items-center space-x-2 text-xs text-slate-400 bg-slate-900/80 border border-slate-800 px-2.5 py-1 rounded font-mono">
          <MapPin className="w-3.5 h-3.5 text-cyan-400" />
          <span>HQ SECTOR ALPHA [25.7617, -80.1918]</span>
        </div>

        {/* Operational Ping */}
        <div className="hidden lg:flex items-center space-x-1.5 text-xs text-slate-400 font-mono">
          <Activity className="w-3.5 h-3.5 text-slate-500" />
          <span>LATENCY: 12ms</span>
        </div>

        {/* Notifications Icon Button */}
        <button 
          type="button" 
          aria-label="Notifications"
          className="relative p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 rounded transition-colors"
          title="System Notifications"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-cyan-500" />
        </button>

        <div className="h-5 w-px bg-slate-800" />

        {/* User/Profile Placeholder (No Auth) */}
        <div className="flex items-center space-x-2 text-slate-300">
          <div className="w-7 h-7 rounded bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
            <UserCheck className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="hidden xl:block text-left font-mono text-[11px]">
            <div className="font-semibold text-slate-200 leading-none">CMD. DISPATCH</div>
            <div className="text-[9px] text-slate-400 leading-tight">DUTY OFFICER</div>
          </div>
        </div>
      </div>
    </header>
  );
};
