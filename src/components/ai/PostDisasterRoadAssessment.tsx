import React, { useState, useEffect, useRef } from 'react';
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
  Compass,
  Upload,
  FileImage,
  RefreshCw,
  Trash2,
  SlidersHorizontal,
  Map
} from 'lucide-react';
import { roadConditionService } from '../../services/roadCondition';
import type { RoadConditionAssessment, RoadSegment } from '../../services/roadCondition';
import { getBackendOrigin, API_BASE_URL } from '../../services/api';

export const PostDisasterRoadAssessment: React.FC = () => {
  // State for assessment result
  const [assessment, setAssessment] = useState<RoadConditionAssessment | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [applying, setApplying] = useState<boolean>(false);
  const [activeSegment, setActiveSegment] = useState<RoadSegment | null>(null);
  const [activeTab, setActiveTab] = useState<'overlay' | 'road_mask' | 'condition_mask' | 'map' | 'before' | 'after'>('overlay');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [analysisStep, setAnalysisStep] = useState<number>(0);

  // File Upload State
  const [beforeFile, setBeforeFile] = useState<File | null>(null);
  const [afterFile, setAfterFile] = useState<File | null>(null);
  const [beforePreview, setBeforePreview] = useState<string | null>(null);
  const [afterPreview, setAfterPreview] = useState<string | null>(null);
  const [beforeDimensions, setBeforeDimensions] = useState<{ width: number; height: number } | null>(null);
  const [afterDimensions, setAfterDimensions] = useState<{ width: number; height: number } | null>(null);

  // Demo Presets Collapsible State
  const [showDemoPresets, setShowDemoPresets] = useState<boolean>(false);

  const beforeInputRef = useRef<HTMLInputElement>(null);
  const afterInputRef = useRef<HTMLInputElement>(null);

  // Load Active Assessment on Mount
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

  // Process File Selection
  const processBeforeFile = (file: File) => {
    setBeforeFile(file);
    const objectUrl = URL.createObjectURL(file);
    setBeforePreview(objectUrl);

    const img = new Image();
    img.onload = () => {
      setBeforeDimensions({ width: img.naturalWidth, height: img.naturalHeight });
    };
    img.src = objectUrl;
  };

  const processAfterFile = (file: File) => {
    setAfterFile(file);
    const objectUrl = URL.createObjectURL(file);
    setAfterPreview(objectUrl);

    const img = new Image();
    img.onload = () => {
      setAfterDimensions({ width: img.naturalWidth, height: img.naturalHeight });
    };
    img.src = objectUrl;
  };

  const handleBeforeFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processBeforeFile(e.target.files[0]);
      setErrorMessage(null);
    }
  };

  const handleAfterFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processAfterFile(e.target.files[0]);
      setErrorMessage(null);
    }
  };

  // Drag & Drop Handlers
  const handleBeforeDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processBeforeFile(e.dataTransfer.files[0]);
      setErrorMessage(null);
    }
  };

  const handleAfterDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processAfterFile(e.dataTransfer.files[0]);
      setErrorMessage(null);
    }
  };

  // Helper to load sample chip presets as File objects
  const handleLoadDemoPreset = async (scenario: string) => {
    setLoading(true);
    setStatusMessage(`Loading sample imagery for ${scenario}...`);
    setErrorMessage(null);
    try {
      let preChip = 'chip0.png';
      let postChip = 'chip1.png';
      if (scenario === 'DEMO_DISASTER') {
        preChip = 'chip1.png';
        postChip = 'chip0.png';
      }

      // Fetch sample chips from backend outputs
      const [respPre, respPost] = await Promise.all([
        fetch(`${getBackendOrigin()}/outputs/${preChip}`).catch(() => null),
        fetch(`${getBackendOrigin()}/outputs/${postChip}`).catch(() => null),
      ]);

      const blobPre = respPre && respPre.ok ? await respPre.blob() : new Blob(['demo'], { type: 'image/png' });
      const blobPost = respPost && respPost.ok ? await respPost.blob() : new Blob(['demo'], { type: 'image/png' });

      const filePre = new File([blobPre], preChip, { type: 'image/png' });
      const filePost = new File([blobPost], postChip, { type: 'image/png' });

      processBeforeFile(filePre);
      processAfterFile(filePost);

      setStatusMessage(`Sample images for ${scenario} loaded into upload inputs. Click ANALYZE ROAD CONDITION to run analysis.`);
    } catch (err: any) {
      setErrorMessage(`Failed to load sample images: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Execute Road Condition Analysis
  const handleAnalyze = async () => {
    setErrorMessage(null);
    setStatusMessage(null);

    // Image Validation Rule
    if (!beforeFile || !afterFile) {
      setErrorMessage('Please upload both BEFORE and AFTER satellite images.');
      return;
    }

    setLoading(true);
    setAnalysisStep(1);

    try {
      // Step 1: Validated
      setAnalysisStep(2);
      // Step 2: Extracting network & Vision AI query
      const res = await roadConditionService.analyzeRoadCondition({
        before_image: beforeFile,
        after_image: afterFile,
      });

      setAnalysisStep(3);
      setAssessment(res);
      setActiveTab('overlay');
      setStatusMessage('Vision AI post-disaster road condition assessment successfully completed.');
    } catch (err: any) {
      console.error('Analysis failed', err);
      const backendUrl = API_BASE_URL;
      const detailMsg = err?.response?.data?.detail || err.message || 'Network request failed';
      setErrorMessage(`Unable to connect to the RESQROUTE backend.\nBackend: ${backendUrl}\nError: ${detailMsg}`);
    } finally {
      setLoading(false);
      setAnalysisStep(0);
    }
  };

  const handleApply = async () => {
    if (!assessment) return;
    setApplying(true);
    setErrorMessage(null);
    try {
      const res = await roadConditionService.applyAssessment(assessment.assessment_id);
      setAssessment(res.active_assessment);
      setStatusMessage('Road network updated successfully. Blocked segments removed from routing graph. Degraded segments weighted 2.5x.');
    } catch (err: any) {
      console.error('Apply failed', err);
      setErrorMessage(`Apply failed: ${err?.message}`);
    } finally {
      setApplying(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      await roadConditionService.resetAssessment();
      if (assessment) {
        setAssessment({ ...assessment, is_active: false });
      }
      setStatusMessage('System routing restored to normal baseline graph.');
    } catch (err: any) {
      console.error('Reset failed', err);
      setErrorMessage(`Reset failed: ${err.message}`);
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

  const resolveImageUrl = (url?: string) => {
    if (!url) return null;
    if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) {
      return url;
    }
    return `${getBackendOrigin()}${url.startsWith('/') ? '' : '/'}${url}`;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8 min-h-screen pb-24 overflow-y-auto">
      {/* Header Banner */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 backdrop-blur-md relative overflow-hidden shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/30 rounded-xl text-cyan-400">
              <ShieldAlert className="w-8 h-8" />
            </div>
            <div>
              <div className="flex items-center space-x-3">
                <h1 className="text-2xl font-extrabold text-white tracking-wide">POST-DISASTER ROAD ASSESSMENT</h1>
                <span className="px-3 py-1 rounded-full text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                  VISION AI
                </span>
              </div>
              <p className="text-sm text-slate-400 mt-1">
                Upload baseline and post-disaster satellite imagery to estimate road traversability changes.
              </p>
            </div>
          </div>

          {/* Action Header Buttons */}
          <div className="flex items-center space-x-3">
            <button
              onClick={handleAnalyze}
              disabled={loading || !beforeFile || !afterFile}
              className="px-5 py-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-sm font-semibold rounded-lg shadow-lg shadow-cyan-900/40 transition-all flex items-center space-x-2 disabled:opacity-50"
            >
              {loading ? <Activity className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
              <span>ANALYZE ROAD CONDITION</span>
            </button>

            {assessment && (
              <button
                onClick={assessment.is_active ? handleReset : handleApply}
                disabled={applying}
                className={`px-5 py-2.5 text-sm font-semibold rounded-lg transition-all flex items-center space-x-2 shadow-lg ${
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
                <span>{assessment.is_active ? 'RESTORE BASELINE GRAPH' : 'APPLY UPDATED ROAD NETWORK'}</span>
              </button>
            )}
          </div>
        </div>

        {/* Disclaimer Callout Banner */}
        <div className="mt-4 p-3 bg-cyan-950/40 border border-cyan-500/30 rounded-lg flex items-center space-x-3 text-cyan-300 text-xs">
          <Info className="w-4 h-4 text-cyan-400 shrink-0" />
          <span className="font-semibold">
            Image-based traversability estimate — not structural safety certification.
          </span>
        </div>

        {/* Active Route Enforcement Alert */}
        {assessment?.is_active && (
          <div className="mt-4 p-3.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-center justify-between text-emerald-300 text-sm">
            <div className="flex items-center space-x-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
              <div>
                <span className="font-bold">ACTIVE POST-DISASTER ROUTING ENFORCED:</span>
                <span className="ml-1 text-slate-300">
                  AI emergency routing engine is actively bypassing blocked roads and penalizing degraded segments.
                </span>
              </div>
            </div>
            <span className="text-xs font-mono bg-emerald-950 px-2.5 py-1 rounded text-emerald-400 border border-emerald-500/30 shrink-0">
              {assessment.blocked_count} BLOCKED ROADS AVOIDED
            </span>
          </div>
        )}

        {/* Status Message Display */}
        {statusMessage && (
          <div className="mt-4 p-3.5 bg-slate-800/90 border border-cyan-500/30 rounded-lg text-cyan-300 text-sm flex items-center space-x-2">
            <Info className="w-4 h-4 text-cyan-400 shrink-0" />
            <span>{statusMessage}</span>
          </div>
        )}

        {/* Error Alert Display */}
        {errorMessage && (
          <div className="mt-4 p-4 bg-red-950/60 border border-red-500/50 rounded-lg text-red-200 text-sm space-y-1">
            <div className="flex items-center space-x-2 font-bold text-red-400">
              <AlertTriangle className="w-5 h-5 shrink-0" />
              <span>ASSESSMENT ERROR</span>
            </div>
            <p className="whitespace-pre-line text-xs font-mono text-red-300">{errorMessage}</p>
          </div>
        )}
      </div>

      {/* STEP 1: UPLOAD IMAGERY CARDS */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-bold text-xs border border-cyan-500/30">
              STEP 1
            </span>
            <h2 className="text-lg font-bold text-white tracking-wide">UPLOAD SATELLITE IMAGERY</h2>
          </div>

          {/* Optional Demo Presets Toggle */}
          <button
            onClick={() => setShowDemoPresets(!showDemoPresets)}
            className="text-xs text-slate-400 hover:text-cyan-300 flex items-center space-x-1.5 font-medium transition-colors"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>{showDemoPresets ? 'Hide Demo Samples' : 'Load Demo Images'}</span>
          </button>
        </div>

        {/* Collapsible Demo Presets Bar */}
        {showDemoPresets && (
          <div className="p-4 bg-slate-900/90 border border-slate-800 rounded-xl flex items-center justify-between flex-wrap gap-3">
            <div className="text-xs text-slate-300">
              <span className="font-semibold text-cyan-400">Sample Imagery Presets: </span>
              <span>Click any scenario below to automatically populate sample BEFORE and AFTER images into the upload dropzones.</span>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleLoadDemoPreset('SECTOR_4_FLOOD')}
                disabled={loading}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-cyan-300 rounded border border-slate-700 transition-all"
              >
                Flood Scenario (Sector 4)
              </button>
              <button
                onClick={() => handleLoadDemoPreset('DEMO_DISASTER')}
                disabled={loading}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-cyan-300 rounded border border-slate-700 transition-all"
              >
                Controlled Demo Scenario
              </button>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* BEFORE DISASTER UPLOAD CARD */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 flex flex-col justify-between shadow-xl relative group">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                  <FileImage className="w-5 h-5 text-cyan-400" />
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    BEFORE DISASTER IMAGE (BASELINE)
                  </h3>
                </div>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                  Pre-Event Imagery
                </span>
              </div>

              <input
                ref={beforeInputRef}
                type="file"
                accept="image/png,image/jpeg,image/jpg,image/webp"
                onChange={handleBeforeFileChange}
                className="hidden"
              />

              {beforePreview ? (
                <div className="relative rounded-lg overflow-hidden border border-slate-700 bg-slate-950 flex flex-col items-center">
                  <img
                    src={beforePreview}
                    alt="Before Disaster Satellite Preview"
                    className="max-h-56 w-full object-cover"
                  />
                  <div className="w-full p-3 bg-slate-950/90 border-t border-slate-800 flex items-center justify-between text-xs">
                    <div>
                      <p className="font-semibold text-slate-200 truncate max-w-[200px]">
                        {beforeFile?.name || 'chip0.png'}
                      </p>
                      <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                        {beforeDimensions ? `${beforeDimensions.width} × ${beforeDimensions.height}` : 'Satellite Capture'} • {beforeFile ? formatFileSize(beforeFile.size) : 'Sample File'}
                      </p>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => beforeInputRef.current?.click()}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded border border-slate-700 transition-colors flex items-center space-x-1"
                      >
                        <RefreshCw className="w-3 h-3" />
                        <span>Replace</span>
                      </button>
                      <button
                        onClick={() => {
                          setBeforeFile(null);
                          setBeforePreview(null);
                          setBeforeDimensions(null);
                        }}
                        className="p-1 text-slate-400 hover:text-red-400 transition-colors"
                        title="Remove Image"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleBeforeDrop}
                  onClick={() => beforeInputRef.current?.click()}
                  className="border-2 border-dashed border-slate-700 hover:border-cyan-500/60 rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer bg-slate-950/50 hover:bg-slate-950/80 transition-all space-y-3"
                >
                  <div className="p-3 bg-slate-900 rounded-full border border-slate-800 text-cyan-400 group-hover:scale-110 transition-transform">
                    <Upload className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-200">
                      Drop baseline satellite image here
                    </p>
                    <p className="text-xs text-slate-400 mt-1">or click to browse from computer</p>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                    PNG, JPG, JPEG, WEBP
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* AFTER DISASTER UPLOAD CARD */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 flex flex-col justify-between shadow-xl relative group">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                  <FileImage className="w-5 h-5 text-amber-400" />
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    AFTER DISASTER IMAGE (POST-EVENT)
                  </h3>
                </div>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                  Post-Event Capture
                </span>
              </div>

              <input
                ref={afterInputRef}
                type="file"
                accept="image/png,image/jpeg,image/jpg,image/webp"
                onChange={handleAfterFileChange}
                className="hidden"
              />

              {afterPreview ? (
                <div className="relative rounded-lg overflow-hidden border border-slate-700 bg-slate-950 flex flex-col items-center">
                  <img
                    src={afterPreview}
                    alt="After Disaster Satellite Preview"
                    className="max-h-56 w-full object-cover"
                  />
                  <div className="w-full p-3 bg-slate-950/90 border-t border-slate-800 flex items-center justify-between text-xs">
                    <div>
                      <p className="font-semibold text-slate-200 truncate max-w-[200px]">
                        {afterFile?.name || 'chip1.png'}
                      </p>
                      <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                        {afterDimensions ? `${afterDimensions.width} × ${afterDimensions.height}` : 'Satellite Capture'} • {afterFile ? formatFileSize(afterFile.size) : 'Sample File'}
                      </p>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => afterInputRef.current?.click()}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded border border-slate-700 transition-colors flex items-center space-x-1"
                      >
                        <RefreshCw className="w-3 h-3" />
                        <span>Replace</span>
                      </button>
                      <button
                        onClick={() => {
                          setAfterFile(null);
                          setAfterPreview(null);
                          setAfterDimensions(null);
                        }}
                        className="p-1 text-slate-400 hover:text-red-400 transition-colors"
                        title="Remove Image"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleAfterDrop}
                  onClick={() => afterInputRef.current?.click()}
                  className="border-2 border-dashed border-slate-700 hover:border-amber-500/60 rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer bg-slate-950/50 hover:bg-slate-950/80 transition-all space-y-3"
                >
                  <div className="p-3 bg-slate-900 rounded-full border border-slate-800 text-amber-400 group-hover:scale-110 transition-transform">
                    <Upload className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-200">
                      Drop post-disaster satellite image here
                    </p>
                    <p className="text-xs text-slate-400 mt-1">or click to browse from computer</p>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                    PNG, JPG, JPEG, WEBP
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* STEP 2: ANALYZE TRIGGER & PROGRESS Checklist */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center space-x-3">
            <span className="px-2.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-bold text-xs border border-cyan-500/30">
              STEP 2
            </span>
            <h2 className="text-lg font-bold text-white tracking-wide">EXECUTE VISION AI ANALYSIS</h2>
          </div>

          <button
            onClick={handleAnalyze}
            disabled={loading || !beforeFile || !afterFile}
            className="px-6 py-3 bg-gradient-to-r from-cyan-600 via-blue-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-bold text-sm rounded-xl shadow-lg shadow-cyan-900/40 transition-all flex items-center space-x-2 disabled:opacity-50"
          >
            {loading ? <Activity className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5 fill-current" />}
            <span>ANALYZE ROAD CONDITION</span>
          </button>
        </div>

        {/* Progress Checklist Banner during loading */}
        {loading && (
          <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-2 text-xs font-mono text-slate-300">
            <div className="flex items-center space-x-2 text-cyan-400 font-bold">
              <Activity className="w-4 h-4 animate-spin" />
              <span>PYTORCH U-NET ROAD SEGMENTATION PIPELINE IN PROGRESS:</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-2">
              <div className="flex items-center space-x-2 text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
                <span>Before image loaded</span>
              </div>
              <div className="flex items-center space-x-2 text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
                <span>After image loaded</span>
              </div>
              <div className={`flex items-center space-x-2 ${analysisStep >= 2 ? 'text-cyan-300 font-bold' : 'text-slate-500'}`}>
                {analysisStep >= 2 ? <Activity className="w-4 h-4 animate-spin text-cyan-400" /> : <span className="w-4 h-4 rounded-full border border-slate-700 inline-block" />}
                <span>Road model loaded & inferring</span>
              </div>
              <div className={`flex items-center space-x-2 ${analysisStep >= 2 ? 'text-cyan-300' : 'text-slate-500'}`}>
                {analysisStep >= 2 ? <Activity className="w-4 h-4 animate-spin text-cyan-400" /> : <span className="w-4 h-4 rounded-full border border-slate-700 inline-block" />}
                <span>Before & After road masks generated</span>
              </div>
              <div className={`flex items-center space-x-2 ${analysisStep >= 3 ? 'text-emerald-400' : 'text-slate-500'}`}>
                {analysisStep >= 3 ? <CheckCircle2 className="w-4 h-4" /> : <span className="w-4 h-4 rounded-full border border-slate-700 inline-block" />}
                <span>Road comparison & segment extraction completed</span>
              </div>
              <div className={`flex items-center space-x-2 ${analysisStep >= 3 ? 'text-emerald-400' : 'text-slate-500'}`}>
                {analysisStep >= 3 ? <CheckCircle2 className="w-4 h-4" /> : <span className="w-4 h-4 rounded-full border border-slate-700 inline-block" />}
                <span>Usability overlay map generated</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* STEP 3: DYNAMIC ASSESSMENT SUMMARY CARDS */}
      {assessment && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-bold text-xs border border-cyan-500/30">
                STEP 3
              </span>
              <h2 className="text-lg font-bold text-white tracking-wide">ASSESSMENT SUMMARY METRICS</h2>
            </div>
            <span className="text-xs font-mono px-3 py-1 rounded bg-slate-800 text-cyan-300 border border-slate-700">
              {assessment.georeference_status || 'IMAGE-SPACE ROAD ASSESSMENT'}
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between shadow-lg">
              <div>
                <p className="text-xs text-slate-400 font-medium uppercase tracking-wider">Road Segments</p>
                <p className="text-2xl font-bold text-white mt-1">{assessment.statistics?.number_of_road_segments ?? assessment.roads_analyzed}</p>
              </div>
              <div className="p-3 bg-slate-800 rounded-lg text-slate-300">
                <Layers className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between shadow-lg">
              <div>
                <p className="text-xs text-slate-400 font-medium uppercase tracking-wider">Road Coverage</p>
                <p className="text-2xl font-bold text-cyan-400 mt-1">
                  {assessment.statistics?.detected_road_coverage_pct != null ? `${assessment.statistics.detected_road_coverage_pct}%` : 'N/A'}
                </p>
              </div>
              <div className="p-3 bg-cyan-500/20 text-cyan-400 rounded-lg border border-cyan-500/30">
                <Activity className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-slate-900/80 border border-emerald-900/40 rounded-xl p-4 flex items-center justify-between shadow-lg">
              <div>
                <p className="text-xs text-emerald-400 font-medium uppercase tracking-wider">DETECTED / USABLE</p>
                <p className="text-2xl font-bold text-emerald-400 mt-1">{assessment.safe_count}</p>
              </div>
              <div className="p-3 bg-emerald-500/20 text-emerald-400 rounded-lg border border-emerald-500/30">
                <CheckCircle2 className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-slate-900/80 border border-amber-900/40 rounded-xl p-4 flex items-center justify-between shadow-lg">
              <div>
                <p className="text-xs text-amber-400 font-medium uppercase tracking-wider">UNCERTAIN</p>
                <p className="text-2xl font-bold text-amber-400 mt-1">{assessment.degraded_count}</p>
              </div>
              <div className="p-3 bg-amber-500/20 text-amber-400 rounded-lg border border-amber-500/30">
                <AlertTriangle className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-slate-900/80 border border-red-900/40 rounded-xl p-4 flex items-center justify-between shadow-lg">
              <div>
                <p className="text-xs text-red-400 font-medium uppercase tracking-wider">NOT DETECTED</p>
                <p className="text-2xl font-bold text-red-400 mt-1">{assessment.blocked_count}</p>
              </div>
              <div className="p-3 bg-red-500/20 text-red-400 rounded-lg border border-red-500/30">
                <XCircle className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between shadow-lg">
              <div>
                <p className="text-xs text-slate-400 font-medium uppercase tracking-wider">Avg Confidence</p>
                <p className="text-2xl font-bold text-slate-300 mt-1">
                  {assessment.statistics?.average_road_confidence != null
                    ? `${(assessment.statistics.average_road_confidence * 100).toFixed(0)}%`
                    : 'N/A'}
                </p>
              </div>
              <div className="p-3 bg-slate-800 text-slate-400 rounded-lg">
                <HelpCircle className="w-5 h-5" />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* STEP 4 & 5: VISUAL RESULTS & SEGMENT INSPECTOR */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Visualizer (2 Columns) */}
        <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden flex flex-col h-[560px] shadow-2xl">
          {/* Tabs header */}
          <div className="bg-slate-950 border-b border-slate-800 px-4 py-3 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center space-x-1.5 flex-wrap gap-y-1">
              <button
                onClick={() => setActiveTab('overlay')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === 'overlay'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                ROAD USABILITY
              </button>
              <button
                onClick={() => setActiveTab('after')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === 'after'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                AFTER ORIGINAL
              </button>
              <button
                onClick={() => setActiveTab('road_mask')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === 'road_mask'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                AFTER ROAD MASK
              </button>
              <button
                onClick={() => setActiveTab('before')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === 'before'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                BEFORE ROAD MASK
              </button>
              <button
                onClick={() => setActiveTab('condition_mask')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === 'condition_mask'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                BEFORE vs AFTER CHANGE
              </button>
              <button
                onClick={() => setActiveTab('map')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === 'map'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                ROAD SEGMENTS
              </button>
            </div>

            {/* Legend */}
            <div className="flex items-center space-x-3 text-xs">
              <span className="flex items-center space-x-1">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                <span className="text-slate-300">DETECTED / USABLE</span>
              </span>
              <span className="flex items-center space-x-1">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                <span className="text-slate-300">UNCERTAIN</span>
              </span>
              <span className="flex items-center space-x-1">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
                <span className="text-slate-300">NOT DETECTED</span>
              </span>
            </div>
          </div>

          {/* Main Visualizer Body */}
          <div className="flex-1 relative">
            {activeTab === 'overlay' ? (
              <div className="w-full h-full bg-slate-950 flex flex-col items-center justify-center p-4 relative overflow-hidden">
                {assessment && (assessment.overlay_image_url || assessment.annotated_after_image || assessment.usability_overlay_url) ? (
                  <div className="relative max-w-full max-h-full flex flex-col items-center justify-center">
                    <img
                      src={resolveImageUrl(assessment.usability_overlay_url || assessment.overlay_image_url || assessment.annotated_after_image)!}
                      alt="Uploaded After Image with Road Usability Markings"
                      className="max-h-[460px] w-auto object-contain rounded-lg border border-slate-700 shadow-2xl"
                    />
                    <div className="mt-2 text-xs text-slate-400 font-mono flex items-center space-x-2">
                      <span>AFTER Image — Road Usability Overlay</span>
                      <span>•</span>
                      <span className="text-cyan-400">🟢 Detected/Usable | 🟡 Uncertain | 🔴 Not Detected</span>
                    </div>
                  </div>
                ) : (
                  <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl max-w-md text-center">
                    <Compass className="w-10 h-10 text-cyan-400 mx-auto mb-3" />
                    <p className="text-white font-semibold text-sm">Road Usability Overlay Ready Upon Assessment</p>
                    <p className="text-slate-400 text-xs mt-1">
                      Upload BEFORE and AFTER satellite images and click <strong className="text-cyan-300">ANALYZE ROAD CONDITION</strong> to generate visually aligned usability overlays.
                    </p>
                  </div>
                )}
              </div>
            ) : activeTab === 'road_mask' ? (
              <div className="w-full h-full bg-slate-950 flex flex-col items-center justify-center p-4 relative overflow-hidden">
                {assessment && assessment.road_mask_url ? (
                  <div className="relative max-w-full max-h-full flex flex-col items-center justify-center">
                    <img
                      src={resolveImageUrl(assessment.road_mask_url)!}
                      alt="Binary Road Segmentation Mask PNG"
                      className="max-h-[460px] w-auto object-contain rounded-lg border border-slate-700 shadow-2xl bg-black"
                    />
                    <div className="mt-2 text-xs text-slate-400 font-mono flex items-center space-x-2">
                      <span>AFTER Road Mask (White = Extracted Road, Black = Background)</span>
                    </div>
                  </div>
                ) : (
                  <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl max-w-md text-center">
                    <FileImage className="w-10 h-10 text-cyan-400 mx-auto mb-3" />
                    <p className="text-white font-semibold text-sm">AFTER Road Mask Ready Upon Assessment</p>
                  </div>
                )}
              </div>
            ) : activeTab === 'before' ? (
              <div className="w-full h-full bg-slate-950 flex flex-col items-center justify-center p-4 relative overflow-hidden">
                {assessment && assessment.before_mask_url ? (
                  <div className="relative max-w-full max-h-full flex flex-col items-center justify-center">
                    <img
                      src={resolveImageUrl(assessment.before_mask_url)!}
                      alt="BEFORE Binary Road Segmentation Mask"
                      className="max-h-[460px] w-auto object-contain rounded-lg border border-slate-700 shadow-2xl bg-black"
                    />
                    <div className="mt-2 text-xs text-slate-400 font-mono flex items-center space-x-2">
                      <span>BEFORE Road Mask (Baseline Neural Net Segmentation)</span>
                    </div>
                  </div>
                ) : (
                  <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl max-w-md text-center">
                    <FileImage className="w-10 h-10 text-cyan-400 mx-auto mb-3" />
                    <p className="text-white font-semibold text-sm">BEFORE Road Mask Ready Upon Assessment</p>
                  </div>
                )}
              </div>
            ) : activeTab === 'condition_mask' ? (
              <div className="w-full h-full bg-slate-950 flex flex-col items-center justify-center p-4 relative overflow-hidden">
                {assessment && (assessment.change_mask_url || assessment.condition_mask_url) ? (
                  <div className="relative max-w-full max-h-full flex flex-col items-center justify-center">
                    <img
                      src={resolveImageUrl(assessment.change_mask_url || assessment.condition_mask_url)!}
                      alt="BEFORE vs AFTER Change Mask PNG"
                      className="max-h-[460px] w-auto object-contain rounded-lg border border-slate-700 shadow-2xl bg-black"
                    />
                    <div className="mt-2 text-xs text-slate-400 font-mono flex items-center space-x-2">
                      <span>BEFORE vs AFTER Change Mask (Green = Retained/Usable, Red = Missing/Unavailable)</span>
                    </div>
                  </div>
                ) : (
                  <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl max-w-md text-center">
                    <FileImage className="w-10 h-10 text-cyan-400 mx-auto mb-3" />
                    <p className="text-white font-semibold text-sm">Change Mask Ready Upon Assessment</p>
                  </div>
                )}
              </div>
            ) : activeTab === 'after' ? (
              <div className="w-full h-full bg-slate-950 flex flex-col items-center justify-center p-4">
                {afterPreview ? (
                  <img
                    src={afterPreview}
                    alt="After Disaster Satellite Image (Raw)"
                    className="max-h-[460px] w-auto object-contain rounded-lg border border-slate-700"
                  />
                ) : (
                  <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl text-center max-w-sm">
                    <FileImage className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                    <p className="text-slate-300 text-sm font-semibold">No After Image Uploaded</p>
                  </div>
                )}
              </div>
            ) : (
              /* ROAD SEGMENTS Tab */
              <div className="w-full h-full bg-slate-950 flex flex-col items-center justify-center p-4 relative overflow-hidden">
                {afterPreview || resolveImageUrl(assessment?.overlay_image_url || assessment?.annotated_after_image) ? (
                  <div className="relative max-w-full max-h-full flex items-center justify-center border border-slate-800 rounded-lg overflow-hidden shadow-2xl">
                    <img
                      src={afterPreview || resolveImageUrl(assessment?.overlay_image_url || assessment?.annotated_after_image)!}
                      alt="Uploaded After Satellite Image Road Network"
                      className="max-h-[460px] w-auto object-contain block"
                    />
                    <svg
                      className="absolute inset-0 w-full h-full pointer-events-auto"
                      viewBox="0 0 512 512"
                      preserveAspectRatio="xMidYMid meet"
                    >
                      {assessment?.segments.map((seg) => {
                        const color = getSegmentColor(seg.condition);
                        const isSelected = activeSegment?.edge_id === seg.edge_id;
                        const pointsStr = seg.pixel_points
                          ? seg.pixel_points.map(([px, py]) => `${px},${py}`).join(' ')
                          : seg.geometry
                              .map(([x, y]) => {
                                const px = x > 180 ? x : Math.min(512, Math.max(0, (x - 77.583) * 20000 + 256));
                                const py = y > 90 ? y : Math.min(512, Math.max(0, (12.980 - y) * 20000 + 256));
                                return `${px},${py}`;
                              })
                              .join(' ');

                        return (
                          <polyline
                            key={seg.edge_id}
                            points={pointsStr}
                            fill="none"
                            stroke={color}
                            strokeWidth={isSelected ? 8 : seg.condition === 'BLOCKED' ? 6 : 4}
                            strokeDasharray={seg.condition === 'BLOCKED' ? '8 4' : undefined}
                            strokeOpacity={isSelected ? 1.0 : 0.85}
                            className="cursor-pointer transition-all hover:stroke-white hover:stroke-[8px]"
                            onClick={() => setActiveSegment(seg)}
                          >
                            <title>{`${seg.edge_id}: ${seg.condition} (${(seg.preservation_ratio * 100).toFixed(0)}%)`}</title>
                          </polyline>
                        );
                      })}
                    </svg>
                  </div>
                ) : (
                  <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl text-center max-w-sm">
                    <Map className="w-8 h-8 text-cyan-400 mx-auto mb-2" />
                    <p className="text-white font-semibold text-sm">Extracted Road Segments Ready Upon Assessment</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* STEP 5: SEGMENT INSPECTOR PANEL (1 Column) */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 flex flex-col justify-between shadow-2xl">
          <div>
            <div className="flex items-center space-x-2 border-b border-slate-800 pb-3 mb-4">
              <MapPin className="w-5 h-5 text-cyan-400" />
              <h2 className="text-base font-bold text-white">SEGMENT INSPECTOR</h2>
            </div>

            {activeSegment ? (
              <div className="space-y-4 text-sm">
                <div>
                  <p className="text-xs text-slate-400 font-medium">Segment ID</p>
                  <p className="font-mono text-cyan-300 font-bold mt-0.5 break-all">{activeSegment.edge_id}</p>
                </div>

                <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between">
                  <span className="text-slate-400 text-xs font-semibold">ESTIMATED CONDITION</span>
                  <span
                    className="px-2.5 py-1 rounded text-xs font-bold"
                    style={{
                      color: getSegmentColor(activeSegment.condition),
                      backgroundColor: `${getSegmentColor(activeSegment.condition)}20`,
                      borderColor: `${getSegmentColor(activeSegment.condition)}40`,
                    }}
                  >
                    {activeSegment.condition === 'SAFE'
                      ? 'DETECTED / USABLE'
                      : activeSegment.condition === 'DEGRADED'
                      ? 'UNCERTAIN'
                      : activeSegment.condition === 'BLOCKED'
                      ? 'NOT DETECTED / UNAVAILABLE'
                      : 'UNKNOWN'}
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

                <div className="space-y-2 border-t border-slate-800 pt-3 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Pre Confidence:</span>
                    <span className="text-slate-200 font-mono">{(activeSegment.pre_confidence * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Post Confidence:</span>
                    <span className="text-slate-200 font-mono">{(activeSegment.post_confidence * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
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
                <p className="text-xs">Click any road segment polyline on the Image Road Map tab to inspect condition metrics.</p>
              </div>
            )}
          </div>

          {/* STEP 6: APPLY BUTTON IN PANEL */}
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
                <span>{assessment.is_active ? 'RESTORE BASELINE ROUTING' : 'APPLY UPDATED ROAD NETWORK'}</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Technical Disclaimer Footer */}
      <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl text-center text-xs text-slate-500">
        <p>Image-based traversability estimate — not structural safety certification.</p>
        <p className="mt-1 text-[11px]">RESQROUTE Stage 7E Post-Disaster Road Assessment Engine</p>
      </div>
    </div>
  );
};
