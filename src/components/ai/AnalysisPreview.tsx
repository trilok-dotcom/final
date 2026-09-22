import React from 'react';
import { Image as ImageIcon, Eye, GitBranch, Layers, Cpu, CheckCircle, Loader2 } from 'lucide-react';
import type { AnalyzeSatelliteResponse } from '../../types/ai';
import { getBackendOrigin } from '../../services/api';

interface AnalysisPreviewProps {
  result?: AnalyzeSatelliteResponse | null;
  originalImageUrl?: string | null;
  isAnalyzing?: boolean;
}

export const AnalysisPreview: React.FC<AnalysisPreviewProps> = ({
  result = null,
  originalImageUrl = null,
  isAnalyzing = false,
}) => {
  const getFullUrl = (path?: string) => {
    if (!path) return undefined;
    if (path.startsWith('http')) return path;
    const backendOrigin = getBackendOrigin();
    return `${backendOrigin}${path.startsWith('/') ? path : '/' + path}`;
  };

  const viewports = [
    {
      id: 'original',
      title: 'Original Satellite Image',
      icon: ImageIcon,
      description: 'Raw high-resolution aerial input viewport',
      imageUrl: originalImageUrl || undefined,
    },
    {
      id: 'mask',
      title: 'AI Road Segmentation',
      icon: Eye,
      description: 'U-Net binary road extraction mask',
      imageUrl: getFullUrl(result?.prediction?.mask_url),
    },
    {
      id: 'skeleton',
      title: 'Extracted Road Skeleton',
      icon: GitBranch,
      description: '1-pixel thin centerline skeleton',
      imageUrl: getFullUrl(result?.road_network?.skeleton_url),
    },
    {
      id: 'overlay',
      title: 'Road Network Overlay',
      icon: Layers,
      description: 'Vector road graph overlay on aerial raster',
      imageUrl: getFullUrl(result?.road_network?.overlay_url),
    },
  ];

  return (
    <div className="bg-[#0b0f19] border border-slate-800 rounded-lg p-5 font-sans select-none space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <h3 className="font-mono font-bold text-sm text-slate-100 tracking-wider uppercase">
            AI ANALYSIS PREVIEW CANVAS
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            4-Quadrant viewports for computer vision road segmentation & graph extraction.
          </p>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
          {result ? 'ANALYSIS COMPLETE' : isAnalyzing ? 'PROCESSING' : 'AWAITING INPUT'}
        </span>
      </div>

      {/* 4 Quadrants Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {viewports.map((vp) => {
          const Icon = vp.icon;
          return (
            <div
              key={vp.id}
              className="bg-[#0f172a]/60 border border-slate-800 rounded-lg p-3.5 flex flex-col justify-between h-64 relative overflow-hidden group hover:border-cyan-500/40 transition-colors"
            >
              {/* Viewport Header */}
              <div className="flex items-center justify-between z-10 bg-slate-950/80 px-2.5 py-1.5 rounded border border-slate-800/80">
                <div className="flex items-center space-x-2">
                  <Icon className="w-4 h-4 text-cyan-400" />
                  <span className="font-mono font-semibold text-xs text-slate-200 uppercase">
                    {vp.title}
                  </span>
                </div>
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                  {vp.id.toUpperCase()}
                </span>
              </div>

              {/* Viewport Image or Canvas Placeholder */}
              <div className="my-auto h-44 w-full rounded bg-slate-950/60 border border-slate-900 overflow-hidden relative flex items-center justify-center">
                {isAnalyzing ? (
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <Loader2 className="w-6 h-6 text-cyan-400 animate-spin" />
                    <span className="text-[11px] font-mono text-cyan-300">Extracting features...</span>
                  </div>
                ) : vp.imageUrl ? (
                  <img
                    src={vp.imageUrl}
                    alt={vp.title}
                    className="w-full h-full object-contain bg-black"
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center text-center p-4">
                    <div className="w-9 h-9 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 mb-1.5">
                      <Cpu className="w-4 h-4" />
                    </div>
                    <span className="text-xs font-mono font-semibold text-slate-400">
                      EMPTY VIEWPORT
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono mt-0.5">
                      {vp.description}
                    </span>
                  </div>
                )}
              </div>

              {/* Footer Status */}
              <div className="text-[10px] font-mono text-slate-400 border-t border-slate-800/60 pt-2 flex items-center justify-between z-10">
                <span>STATUS: {vp.imageUrl ? 'RENDERED' : 'READY'}</span>
                <span>MODEL: U-NET RESNET-34</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Real Model Extraction Metrics Panel */}
      {result && (
        <div className="bg-slate-900/80 border border-cyan-500/30 rounded-lg p-4 font-mono text-xs text-slate-300 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center space-x-2 text-cyan-400 font-bold">
              <CheckCircle className="w-4 h-4 text-emerald-400" />
              <span>REAL AI EXTRACTION METRICS</span>
            </div>
            <span className="text-[10px] text-slate-400">STAGE 3B DYNAMIC GRAPH</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
              <div className="text-[10px] text-slate-400 uppercase">AI Confidence</div>
              <div className="text-sm font-bold text-cyan-400 mt-0.5">
                {(result.prediction.confidence * 100).toFixed(1)}%
              </div>
            </div>

            <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
              <div className="text-[10px] text-slate-400 uppercase">Road Coverage</div>
              <div className="text-sm font-bold text-emerald-400 mt-0.5">
                {result.road_network.coverage_percentage.toFixed(2)}%
              </div>
            </div>

            <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
              <div className="text-[10px] text-slate-400 uppercase">Graph Nodes</div>
              <div className="text-sm font-bold text-amber-400 mt-0.5">
                {result.road_network.graph_nodes}
              </div>
            </div>

            <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
              <div className="text-[10px] text-slate-400 uppercase">Graph Edges</div>
              <div className="text-sm font-bold text-indigo-400 mt-0.5">
                {result.road_network.graph_edges}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
