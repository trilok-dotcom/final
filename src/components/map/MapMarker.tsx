import L from 'leaflet';

// Custom DivIcon generator for tactical emergency map markers
export function createIncidentMarkerIcon(severity: string, title: string) {
  const sevUpper = severity.toUpperCase();
  let colorClass = 'bg-amber-500 border-amber-300 text-amber-950';
  let pulseClass = 'bg-amber-500/40';

  if (sevUpper === 'CRITICAL') {
    colorClass = 'bg-red-600 border-red-300 text-white';
    pulseClass = 'bg-red-600/50 animate-radar-ping';
  } else if (sevUpper === 'HIGH') {
    colorClass = 'bg-orange-500 border-orange-300 text-white';
    pulseClass = 'bg-orange-500/40 animate-pulse';
  } else if (sevUpper === 'MEDIUM' || sevUpper === 'MODERATE') {
    colorClass = 'bg-amber-500 border-amber-300 text-slate-950';
    pulseClass = 'bg-amber-500/30';
  } else if (sevUpper === 'LOW') {
    colorClass = 'bg-emerald-500 border-emerald-300 text-slate-950';
    pulseClass = 'bg-emerald-500/30';
  }

  const html = `
    <div class="relative flex items-center justify-center w-8 h-8 group">
      <div class="absolute inset-0 rounded-full ${pulseClass}"></div>
      <div class="relative w-6 h-6 rounded-full ${colorClass} border-2 flex items-center justify-center font-mono font-bold text-[10px] shadow-lg">
        !
      </div>
      <div class="absolute bottom-full mb-1 hidden group-hover:block bg-slate-900 border border-slate-700 text-slate-200 text-[10px] font-mono px-2 py-0.5 rounded shadow-xl whitespace-nowrap z-50">
        ${title} (${sevUpper})
      </div>
    </div>
  `;

  return L.divIcon({
    html,
    className: 'custom-incident-marker',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
}

export function createRescueUnitMarkerIcon(
  callsign: string,
  type: string,
  status: string = 'AVAILABLE',
  heading: number = 0
) {
  const typeUpper = type.toUpperCase();
  const statusUpper = status.toUpperCase();

  let typeCode = 'UT';
  if (typeUpper.includes('AMBULANCE')) typeCode = 'AMB';
  else if (typeUpper.includes('FIRE')) typeCode = 'FIRE';
  else if (typeUpper.includes('POLICE')) typeCode = 'POL';
  else if (typeUpper.includes('RESCUE')) typeCode = 'RES';
  else if (typeUpper.includes('DISASTER')) typeCode = 'DIS';

  let borderClass = 'border-cyan-400 text-cyan-300';
  let pulseClass = 'bg-cyan-500/30 animate-pulse';

  if (statusUpper === 'AVAILABLE') {
    borderClass = 'border-emerald-400 text-emerald-300';
    pulseClass = 'bg-emerald-500/30 animate-pulse';
  } else if (statusUpper === 'EN_ROUTE' || statusUpper === 'DISPATCHED') {
    borderClass = 'border-amber-400 text-amber-300';
    pulseClass = 'bg-amber-500/40 animate-pulse';
  } else if (statusUpper === 'ON_SCENE') {
    borderClass = 'border-purple-400 text-purple-300';
    pulseClass = 'bg-purple-500/40 animate-pulse';
  } else if (statusUpper === 'OFFLINE') {
    borderClass = 'border-slate-600 text-slate-400';
    pulseClass = 'bg-slate-700/20';
  }

  const rotateStyle = heading > 0 ? `transform: rotate(${heading}deg); transition: transform 0.4s ease;` : '';

  const html = `
    <div class="relative flex items-center justify-center w-8 h-8 group">
      <div class="absolute inset-0 rounded ${pulseClass}"></div>
      <div class="relative w-7 h-6 rounded bg-slate-950 border ${borderClass} flex items-center justify-center font-mono font-bold text-[9px] shadow-lg" style="${rotateStyle}">
        ${typeCode}
      </div>
      <div class="absolute bottom-full mb-1 hidden group-hover:block bg-slate-900 border border-slate-700 text-slate-200 text-[10px] font-mono px-2 py-0.5 rounded shadow-xl whitespace-nowrap z-50">
        UNIT: ${callsign} (${typeUpper}) [${statusUpper}] ${heading > 0 ? `(${heading.toFixed(0)}°)` : ''}
      </div>
    </div>
  `;

  return L.divIcon({
    html,
    className: 'custom-unit-marker',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
}

export function createLocationPinIcon(type: 'start' | 'destination') {
  const isStart = type === 'start';
  const colorClass = isStart ? 'bg-emerald-500 border-emerald-300 text-slate-950' : 'bg-purple-600 border-purple-300 text-white';
  const label = isStart ? 'A' : 'B';

  const html = `
    <div class="relative flex items-center justify-center w-8 h-8">
      <div class="w-6 h-6 rounded-full ${colorClass} border-2 flex items-center justify-center font-mono font-bold text-[11px] shadow-lg">
        ${label}
      </div>
    </div>
  `;

  return L.divIcon({
    html,
    className: `custom-location-pin-${type}`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
}
