import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  HelpCircle, 
  Play, 
  RotateCcw, 
  Check, 
  Layers, 
  Activity,
  Info,
  MapPin,
  Compass
} from 'lucide-react';
import { MapContainer, TileLayer, Polyline, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { roadConditionService } from '../../services/roadCondition';
import type { RoadConditionAssessment, RoadSegment } from '../../services/roadCondition';


// Map Center Controller
const MapBoundsController: React.FC<{ segments: RoadSegment[] }> = ({ segments }) => {
  const map = useMap();
  useEffect(() => {
    if (segments.length > 0) {
      const allCoords: [number, number][] = [];
      segments.forEach((seg) => {
        seg.geometry.forEach(([lng, lat]) => {
          allCoords.push([lat, lng]);
        });
      });
      if (allCoords.length > 0) {
        const bounds = L.latLngBounds(allCoords);
        map.fitBounds(bounds, { padding: [40, 40] });
      }
    }
  }, [segments, map]);
  return null;
};

export const PostDisasterRoadAssessment: React.FC = () => {
  const [assessment, setAssessment] = useState<RoadConditionAssessment | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [applying, setApplying] = useState<boolean>(false);
  const [activeSegment, setActiveSegment] = useState<RoadSegment | null>(null);
  const [activeTab, setActiveTab] = useState<'map' | 'before' | 'after'>('map');
  const [preImage, setPreImage] = useState<string>('chip0.png');
  const [postImage, setPostImage] = useState<string>('chip1.png');
  const [demoScenario, setDemoScenario] = useState<string>('SECTOR_4_FLOOD');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const fetchActive = async () => {
    try {
      const res = await roadConditionService.getActiveAssessment();
      if (res.active && res.assessment) {
        setAssessment(res.assessment);
      }
    } catch (e) {
      console.error('Failed to fetch active assessment', e);
    }
  };

  useEffect(() => {
    fetchActive();
  }, []);

  const handleAnalyze = async () => {
    setLoading(true);
    setStatusMessage(null);
    try {
      const res = await roadConditionService.analyzeRoadCondition({
        pre_image_name: preImage,
        post_image_name: postImage,
        demo_scenario: demoScenario,
      });
      setAssessment(res);
      setStatusMessage('Image-based post-disaster road condition analysis completed.');
    } catch (err: any) {
      console.error('Analysis failed', err);
      setStatusMessage(`Analysis failed: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async () => {
    if (!assessment) return;
    setApplying(true);
    try {
      const res = await roadConditionService.applyAssessment(assessment.assessment_id);
      setAssessment(res.active_assessment);
      setStatusMessage('Post-disaster road conditions successfully APPLIED to active AI routing!');
    } catch (err: any) {
      console.error('Apply failed', err);
      setStatusMessage(`Apply failed: ${err?.message}`);
    } finally {
      setApplying(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await roadConditionService.resetAssessment();
      if (assessment) {
        setAssessment({ ...assessment, is_active: false });
      }
      setStatusMessage('System routing restored to normal baseline graph.');
    } catch (err: any) {
      console.error('Reset failed', err);
    } finally {
      setLoading(false);
    }
  };

  const getSegmentColor = (condition: string) => {
    switch (condition) {
      case 'SAFE':
        return '#10B981'; // Emerald Green
      case 'DEGRADED':
        return '#F59E0B'; // Amber Yellow
      case 'BLOCKED':
        return '#EF4444'; // Bright Red
      default:
        return '#9CA3AF'; // Gray
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 backdrop-blur-md relative overflow-hidden shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="flex items-center space-x-3">
              <div className="p-2.5 bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/30 rounded-lg text-cyan-400">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h1 className="text-xl font-bold text-white tracking-wide">POST-DISASTER ROAD ASSESSMENT</h1>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                    STAGE 7E INTEGRATION
                  </span>
                </div>
                <p className="text-sm text-slate-400 mt-0.5">
                  Image-based post-disaster road condition estimation comparing baseline satellite vs post-event imagery
                </p>
              </div>
            </div>
          </div>

          {/* Quick Demo Controls */}
          <div className="flex items-center space-x-3">
            <button
              onClick={handleAnalyze}
              disabled={loading}
              className="px-4 py-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-sm font-semibold rounded-lg shadow-lg shadow-cyan-900/40 transition-all flex items-center space-x-2 disabled:opacity-50"
            >
              {loading ? <Activity className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
              <span>ANALYZE ROAD CONDITION</span>
            </button>

            {assessment && (
              <button
                onClick={assessment.is_active ? handleReset : handleApply}
                disabled={applying}
                className={`px-4 py-2.5 text-sm font-semibold rounded-lg transition-all flex items-center space-x-2 shadow-lg ${
                  assessment.is_active
                    ? 'bg-amber-600/30 text-amber-300 border border-amber-500/50 hover:bg-amber-600/40'
                    : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-900/40'
                }`}
              >
                {applying ? (
                  <Activity className="w-4 h-4 animate-spin" />
                ) : assessment.is_active ? (
                  <RotateCcw className="w-4 h-4" />
                ) : (
                  <Check className="w-4 h-4" />
                )}
                <span>{assessment.is_active ? 'RESET BASELINE' : 'APPLY UPDATED ROAD NETWORK'}</span>
              </button>
            )}
          </div>
        </div>

        {/* Active Route Enforcement Alert */}
        {assessment?.is_active && (
          <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-center justify-between text-emerald-300 text-sm">
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span className="font-semibold">ACTIVE POST-DISASTER ROUTING ENFORCED:</span>
              <span>AI emergency routing engine is actively bypassing blocked roads and penalizing degraded segments.</span>
            </div>
            <span className="text-xs font-mono bg-emerald-950 px-2 py-1 rounded text-emerald-400 border border-emerald-500/30">
              {assessment.blocked_count} BLOCKED ROADS AVOIDED
            </span>
          </div>
        )}

        {statusMessage && !assessment?.is_active && (
          <div className="mt-4 p-3 bg-slate-800/80 border border-slate-700 rounded-lg text-slate-300 text-sm flex items-center space-x-2">
            <Info className="w-4 h-4 text-cyan-400" />
            <span>{statusMessage}</span>
          </div>
        )}
      </div>

      {/* Control Panel: Image Selection / Scenario Selection */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
            PRE-DISASTER IMAGE (BASELINE)
          </label>
          <select
            value={preImage}
            onChange={(e) => setPreImage(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
          >
            <option value="chip0.png">chip0.png (Georeferenced Sector 4 Baseline)</option>
            <option value="chip1.png">chip1.png (Georeferenced Sector 1 Baseline)</option>
            <option value="chip10.png">chip10.png (Urban Corridor Baseline)</option>
          </select>
        </div>

        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
            AFTER DISASTER IMAGE
          </label>
          <select
            value={postImage}
            onChange={(e) => setPostImage(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
          >
            <option value="chip1.png">chip1.png (Post-Disaster Capture)</option>
            <option value="chip0.png">chip0.png (Baseline Compare)</option>
          </select>
        </div>

        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
            DEMO SCENARIO MODE
          </label>
          <select
            value={demoScenario}
            onChange={(e) => setDemoScenario(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
          >
            <option value="SECTOR_4_FLOOD">Sector 4 Disaster Flood Scenario</option>
            <option value="DEMO_DISASTER">Controlled Demo Road Blockage</option>
          </select>
        </div>
      </div>

      {/* Summary Cards */}
      {assessment && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium uppercase">Roads Analyzed</p>
              <p className="text-2xl font-bold text-white mt-1">{assessment.roads_analyzed}</p>
            </div>
            <div className="p-3 bg-slate-800 rounded-lg text-slate-300">
              <Layers className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-slate-900/70 border border-emerald-900/40 rounded-xl p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-emerald-400 font-medium uppercase">SAFE</p>
              <p className="text-2xl font-bold text-emerald-400 mt-1">{assessment.safe_count}</p>
            </div>
            <div className="p-3 bg-emerald-500/20 text-emerald-400 rounded-lg border border-emerald-500/30">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-slate-900/70 border border-amber-900/40 rounded-xl p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-amber-400 font-medium uppercase">DEGRADED</p>
              <p className="text-2xl font-bold text-amber-400 mt-1">{assessment.degraded_count}</p>
            </div>
            <div className="p-3 bg-amber-500/20 text-amber-400 rounded-lg border border-amber-500/30">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-slate-900/70 border border-red-900/40 rounded-xl p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-red-400 font-medium uppercase">BLOCKED</p>
              <p className="text-2xl font-bold text-red-400 mt-1">{assessment.blocked_count}</p>
            </div>
            <div className="p-3 bg-red-500/20 text-red-400 rounded-lg border border-red-500/30">
              <XCircle className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium uppercase">UNKNOWN</p>
              <p className="text-2xl font-bold text-slate-400 mt-1">{assessment.unknown_count}</p>
            </div>
            <div className="p-3 bg-slate-800 text-slate-400 rounded-lg">
              <HelpCircle className="w-5 h-5" />
            </div>
          </div>
        </div>
      )}

      {/* Main Map & Inspector Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map Visualizer (2 Columns) */}
        <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden flex flex-col h-[520px]">
          {/* Tabs */}
          <div className="bg-slate-950 border-b border-slate-800 px-4 py-2.5 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setActiveTab('map')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === 'map'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                ROAD CONDITION MAP
              </button>
              <button
                onClick={() => setActiveTab('before')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === 'before'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                BEFORE DISASTER (BASELINE)
              </button>
              <button
                onClick={() => setActiveTab('after')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === 'after'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                AFTER DISASTER
              </button>
            </div>

            {/* Legend */}
            <div className="flex items-center space-x-3 text-xs">
              <span className="flex items-center space-x-1">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                <span className="text-slate-300">SAFE</span>
              </span>
              <span className="flex items-center space-x-1">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                <span className="text-slate-300">DEGRADED</span>
              </span>
              <span className="flex items-center space-x-1">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
                <span className="text-slate-300">BLOCKED</span>
              </span>
            </div>
          </div>

          {/* Map View */}
          <div className="flex-1 relative">
            {activeTab === 'map' ? (
              <MapContainer
                center={[12.9716, 77.5946]}
                zoom={14}
                className="w-full h-full"
                scrollWheelZoom={true}
              >
                <TileLayer
                  url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                  attribution='&copy; <a href="https://carto.com/">CARTO</a>'
                />

                {assessment && <MapBoundsController segments={assessment.segments} />}

                {assessment?.segments.map((seg) => {
                  const leafletCoords: [number, number][] = seg.geometry.map(([lng, lat]) => [lat, lng]);
                  const color = getSegmentColor(seg.condition);
                  const isSelected = activeSegment?.edge_id === seg.edge_id;

                  return (
                    <Polyline
                      key={seg.edge_id}
                      positions={leafletCoords}
                      pathOptions={{
                        color,
                        weight: isSelected ? 8 : seg.condition === 'BLOCKED' ? 6 : 4,
                        opacity: isSelected ? 1.0 : seg.condition === 'BLOCKED' ? 0.95 : 0.85,
                        dashArray: seg.condition === 'BLOCKED' ? '8, 8' : undefined,
                      }}
                      eventHandlers={{
                        click: () => setActiveSegment(seg),
                      }}
                    >
                      <Popup className="custom-popup">
                        <div className="p-1 text-slate-900 text-xs">
                          <p className="font-bold">{seg.edge_id}</p>
                          <p className="capitalize font-semibold mt-1" style={{ color }}>
                            Condition: {seg.condition}
                          </p>
                          <p>Preservation: {(seg.preservation_ratio * 100).toFixed(1)}%</p>
                          <p>Traversable: {seg.traversable ? 'YES' : 'NO (BLOCKED)'}</p>
                        </div>
                      </Popup>
                    </Polyline>
                  );
                })}
              </MapContainer>
            ) : (
              <div className="w-full h-full bg-slate-950 flex flex-col items-center justify-center p-6 text-center">
                <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl max-w-md">
                  <Compass className="w-8 h-8 text-cyan-400 mx-auto mb-2" />
                  <p className="text-white font-semibold text-sm">
                    {activeTab === 'before' ? 'Pre-Disaster Baseline Image' : 'Post-Disaster Image Capture'}
                  </p>
                  <p className="text-slate-400 text-xs mt-1">
                    Showing georeferenced satellite chip {activeTab === 'before' ? preImage : postImage} used in image-based road estimation.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Road Segment Detail Inspector Panel (1 Column) */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 border-b border-slate-800 pb-3 mb-4">
              <MapPin className="w-5 h-5 text-cyan-400" />
              <h2 className="text-base font-bold text-white">SEGMENT INSPECTOR</h2>
            </div>

            {activeSegment ? (
              <div className="space-y-4 text-sm">
                <div>
                  <p className="text-xs text-slate-400 font-medium">Road Segment ID</p>
                  <p className="font-mono text-cyan-300 font-bold mt-0.5 break-all">{activeSegment.edge_id}</p>
                </div>

                <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between">
                  <span className="text-slate-400 text-xs font-semibold">CONDITION</span>
                  <span
                    className="px-2.5 py-1 rounded text-xs font-bold"
                    style={{
                      color: getSegmentColor(activeSegment.condition),
                      backgroundColor: `${getSegmentColor(activeSegment.condition)}20`,
                      borderColor: `${getSegmentColor(activeSegment.condition)}40`,
                    }}
                  >
                    {activeSegment.condition}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg">
                    <p className="text-xs text-slate-400">Preservation Ratio</p>
                    <p className="text-lg font-bold text-white mt-1">
                      {(activeSegment.preservation_ratio * 100).toFixed(1)}%
                    </p>
                  </div>
                  <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg">
                    <p className="text-xs text-slate-400">Condition Score</p>
                    <p className="text-lg font-bold text-white mt-1">{activeSegment.condition_score}/100</p>
                  </div>
                </div>

                <div className="space-y-2 border-t border-slate-800 pt-3">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400">Pre-Disaster Confidence:</span>
                    <span className="text-slate-200 font-mono">{(activeSegment.pre_confidence * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400">Post-Disaster Confidence:</span>
                    <span className="text-slate-200 font-mono">{(activeSegment.post_confidence * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400">Graph Connectivity:</span>
                    <span className="text-slate-200 font-mono">{activeSegment.connectivity}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400">Emergency Traversable:</span>
                    <span
                      className={`font-semibold ${
                        activeSegment.traversable ? 'text-emerald-400' : 'text-red-400'
                      }`}
                    >
                      {activeSegment.traversable ? 'YES' : 'NO (BLOCKED)'}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-slate-500">
                <Info className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-xs">Click any road segment polyline on the map to inspect condition metrics.</p>
              </div>
            )}
          </div>

          {/* Action Button */}
          {assessment && (
            <div className="pt-4 border-t border-slate-800 mt-4">
              <button
                onClick={assessment.is_active ? handleReset : handleApply}
                disabled={applying}
                className={`w-full py-3 text-sm font-bold rounded-lg transition-all flex items-center justify-center space-x-2 shadow-lg ${
                  assessment.is_active
                    ? 'bg-amber-600 hover:bg-amber-500 text-white'
                    : 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-emerald-900/30'
                }`}
              >
                <span>{assessment.is_active ? 'RESTORE BASELINE NETWORK' : 'APPLY UPDATED ROAD NETWORK'}</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
