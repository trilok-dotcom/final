import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Navigation, 
  AlertTriangle, 
  ShieldCheck, 
  Cpu, 
  Activity, 
  Settings, 
  ChevronLeft, 
  ChevronRight,
  Radio
} from 'lucide-react';

interface SidebarProps {
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  collapsed: externalCollapsed, 
  onToggleCollapse 
}) => {
  const [internalCollapsed, setInternalCollapsed] = useState(false);
  
  const isCollapsed = externalCollapsed !== undefined ? externalCollapsed : internalCollapsed;
  const toggleCollapse = onToggleCollapse || (() => setInternalCollapsed(!internalCollapsed));

  const navItems = [
    {
      label: 'Evaluation Center',
      path: '/evaluation-center',
      icon: Activity,
      badge: 'ST 10',
      badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    },
    {
      label: 'Command Center',
      path: '/command-center',
      icon: Radio,
      badge: 'ST 9A',
      badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    },
    {
      label: 'Simulation Center',
      path: '/simulation-center',
      icon: Cpu,
      badge: 'ST 9B',
      badgeColor: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
    },
    {
      label: 'Dashboard',
      path: '/',
      icon: LayoutDashboard,
    },
    {
      label: 'Route Planning',
      path: '/route-planning',
      icon: Navigation,
    },
    {
      label: 'Incidents',
      path: '/incidents',
      icon: AlertTriangle,
      badge: '2 CRIT',
      badgeColor: 'bg-red-500/20 text-red-400 border-red-500/40',
    },
    {
      label: 'Rescue Units',
      path: '/rescue-units',
      icon: ShieldCheck,
      badge: '12 UNIT',
      badgeColor: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40',
    },
    {
      label: 'AI Analysis',
      path: '/ai-analysis',
      icon: Cpu,
    },
  ];

  return (
    <aside
      className={`bg-[#0b0f19] border-r border-slate-800/80 flex flex-col justify-between transition-all duration-300 z-30 relative select-none ${
        isCollapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div>
        <div className="h-16 px-4 flex items-center justify-between border-b border-slate-800/60">
          {!isCollapsed ? (
            <div>
              <div className="flex items-center space-x-2">
                <Radio className="w-5 h-5 text-cyan-400 animate-pulse" />
                <span className="font-mono font-bold tracking-widest text-slate-100 text-base">
                  RESQROUTE
                </span>
              </div>
              <p className="text-[10px] text-slate-400 uppercase tracking-tight font-medium">
                Emergency Response Intelligence
              </p>
            </div>
          ) : (
            <div className="mx-auto text-cyan-400">
              <Radio className="w-6 h-6 animate-pulse" />
            </div>
          )}

          <button
            type="button"
            onClick={toggleCollapse}
            className="p-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-colors hidden md:flex items-center justify-center"
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Navigation List */}
        <nav className="p-2 space-y-1 mt-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-3 py-2.5 rounded text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                {!isCollapsed && (
                  <div className="flex items-center justify-between w-full">
                    <span className="truncate">{item.label}</span>
                    {item.badge && (
                      <span className={`text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded border ${item.badgeColor}`}>
                        {item.badge}
                      </span>
                    )}
                  </div>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Bottom Actions & Status */}
      <div className="p-2 border-t border-slate-800/60 space-y-1">
        {/* System Status Link / Indicator */}
        <div
          className={`flex items-center space-x-3 px-3 py-2 rounded text-xs text-slate-400 bg-slate-900/60 border border-slate-800/60 font-mono ${
            isCollapsed ? 'justify-center px-0' : ''
          }`}
        >
          <Activity className="w-4 h-4 text-emerald-400 shrink-0" />
          {!isCollapsed && (
            <div className="w-full flex items-center justify-between text-[11px]">
              <span className="text-slate-300 font-semibold">System Status</span>
              <span className="text-[10px] text-emerald-400">100% ONLINE</span>
            </div>
          )}
        </div>

        {/* Settings button placeholder */}
        <button
          type="button"
          className={`w-full flex items-center space-x-3 px-3 py-2 rounded text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors font-medium ${
            isCollapsed ? 'justify-center px-0' : ''
          }`}
          title="Settings (Connected in Stage 2+)"
        >
          <Settings className="w-4 h-4 shrink-0" />
          {!isCollapsed && <span>Settings</span>}
        </button>
      </div>
    </aside>
  );
};
