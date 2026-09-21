import React, { useState } from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { SatelliteUpload } from '../components/ai/SatelliteUpload';
import { AnalysisPreview } from '../components/ai/AnalysisPreview';
import { Cpu, Image as ImageIcon, Eye, GitBranch, Navigation, ArrowRight } from 'lucide-react';
import { uploadSatelliteImage } from '../services/ai';
import type { AnalyzeSatelliteResponse } from '../types/ai';

export const AIAnalysisPage: React.FC = () => {
  const [analysisResult, setAnalysisResult] = useState<AnalyzeSatelliteResponse | null>(null);
  const [originalImageUrl, setOriginalImageUrl] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const workflowSteps = [
    {
      step: '01',
      title: 'Satellite Image',
      icon: ImageIcon,
      description: 'High-res raster aerial input',
      status: originalImageUrl ? 'ACTIVE' : 'IDLE',
    },
    {
      step: '02',
      title: 'AI Road Segmentation',
      icon: Eye,
      description: 'U-Net ResNet-34 feature extraction',
      status: analysisResult ? 'COMPLETED' : isAnalyzing ? 'PROCESSING' : 'IDLE',
    },
    {
      step: '03',
      title: 'Road Network',
      icon: GitBranch,
      description: 'NetworkX graph nodes & edges',
      status: analysisResult ? 'COMPLETED' : isAnalyzing ? 'PROCESSING' : 'IDLE',
    },
    {
      step: '04',
      title: 'Routing Engine',
      icon: Navigation,
      description: 'OSRM & disaster route solver',
      status: analysisResult ? 'READY' : 'STANDBY',
    },
  ];

  const handleFileUpload = async (file: File) => {
    setIsAnalyzing(true);
    setError(null);
    setAnalysisResult(null);

    // Create local object URL for preview
    const previewUrl = URL.createObjectURL(file);
    setOriginalImageUrl(previewUrl);

    try {
      const response = await uploadSatelliteImage(file);
      setAnalysisResult(response);
    } catch (err) {
      console.error('Satellite analysis error:', err);
      setError(err instanceof Error ? err.message : 'Satellite analysis failed.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <PageContainer>
      <div className="flex-1 flex flex-col h-full overflow-y-auto bg-[#090d16] p-6 space-y-6 select-none font-sans">
        {/* Page Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <div className="flex items-center space-x-2">
              <Cpu className="w-5 h-5 text-cyan-400" />
              <h2 className="font-mono font-bold text-lg tracking-wider text-slate-100 uppercase">
                AI ROAD ANALYSIS & SATELLITE EXTRACTION
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Deep learning U-Net satellite segmentation & real road graph extraction pipeline.
            </p>
          </div>

          <span className="text-xs font-mono px-3 py-1 rounded bg-slate-900 text-cyan-400 border border-slate-800 hidden sm:inline">
            STAGE 3B ACTIVE: U-NET + ROAD GRAPH
          </span>
        </div>

        {/* Workflow Pipeline Banner */}
        <div className="bg-[#0b0f19] border border-slate-800 rounded-lg p-4 font-mono">
          <div className="text-xs font-bold text-slate-300 uppercase mb-3 flex items-center justify-between">
            <span>PIPELINE ARCHITECTURE WORKFLOW</span>
            <span className="text-[11px] text-cyan-400 font-bold">
              SATELLITE &rarr; AI SEGMENTATION &rarr; ROAD NETWORK &rarr; ROUTING
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 relative">
            {workflowSteps.map((ws, idx) => {
              const Icon = ws.icon;
              return (
                <div
                  key={ws.step}
                  className={`bg-slate-900/60 border p-3 rounded flex items-start space-x-3 relative transition-colors ${
                    ws.status === 'COMPLETED'
                      ? 'border-emerald-500/50 bg-emerald-950/20'
                      : ws.status === 'PROCESSING'
                      ? 'border-cyan-500/50 bg-cyan-950/20'
                      : 'border-slate-800'
                  }`}
                >
                  <div className="w-8 h-8 rounded bg-cyan-950/60 border border-cyan-800/80 flex items-center justify-center text-cyan-400 shrink-0 mt-0.5">
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center space-x-1.5">
                      <span className="text-[10px] text-cyan-400 font-bold">[{ws.step}]</span>
                      <span className="text-xs font-bold text-slate-200">{ws.title}</span>
                    </div>
                    <p className="text-[10px] text-slate-400 mt-0.5">{ws.description}</p>
                  </div>

                  {idx < workflowSteps.length - 1 && (
                    <div className="hidden lg:block absolute -right-3.5 top-1/2 -translate-y-1/2 z-10 text-slate-600">
                      <ArrowRight className="w-4 h-4" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Main Grid: Upload & Preview */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <SatelliteUpload
              onFileSelect={handleFileUpload}
              isAnalyzing={isAnalyzing}
              error={error}
              hasResult={!!analysisResult}
            />
          </div>

          <div className="lg:col-span-2">
            <AnalysisPreview
              result={analysisResult}
              originalImageUrl={originalImageUrl}
              isAnalyzing={isAnalyzing}
            />
          </div>
        </div>
      </div>
    </PageContainer>
  );
};
