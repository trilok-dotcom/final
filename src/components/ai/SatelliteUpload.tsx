import React, { useState } from 'react';
import { UploadCloud, FileCheck, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';

interface SatelliteUploadProps {
  onFileSelect?: (file: File) => void;
  isAnalyzing?: boolean;
  error?: string | null;
  hasResult?: boolean;
}

export const SatelliteUpload: React.FC<SatelliteUploadProps> = ({
  onFileSelect,
  isAnalyzing = false,
  error = null,
  hasResult = false,
}) => {
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFileName(file.name);
      if (onFileSelect) {
        onFileSelect(file);
      }
    }
  };

  return (
    <div className="bg-[#0b0f19] border border-slate-800 rounded-lg p-5 font-sans select-none space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <h3 className="font-mono font-bold text-sm text-slate-100 tracking-wider uppercase">
            UPLOAD SATELLITE IMAGE
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Select high-resolution aerial or satellite raster image for road extraction.
          </p>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
          U-NET INPUT
        </span>
      </div>

      {/* Drag & Drop Box */}
      <div className="relative border-2 border-dashed border-slate-800 hover:border-cyan-500/50 rounded-lg p-8 text-center transition-colors bg-slate-900/30 group cursor-pointer">
        <input
          type="file"
          accept=".jpg,.jpeg,.png,.tif,.tiff"
          disabled={isAnalyzing}
          onChange={handleFileChange}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10 disabled:cursor-not-allowed"
        />

        <div className="flex flex-col items-center justify-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-slate-800 group-hover:bg-cyan-950/40 border border-slate-700 group-hover:border-cyan-500/40 flex items-center justify-center text-slate-400 group-hover:text-cyan-400 transition-colors">
            {isAnalyzing ? (
              <Loader2 className="w-6 h-6 text-cyan-400 animate-spin" />
            ) : (
              <UploadCloud className="w-6 h-6" />
            )}
          </div>

          <div>
            <div className="text-sm font-semibold text-slate-200">
              {isAnalyzing ? (
                <span className="text-cyan-300 font-mono">Running U-Net Neural Analysis...</span>
              ) : selectedFileName ? (
                <span className="text-cyan-300 font-mono flex items-center justify-center space-x-1.5">
                  <FileCheck className="w-4 h-4 text-emerald-400" />
                  <span>{selectedFileName}</span>
                </span>
              ) : (
                'Drop satellite imagery here or click to browse'
              )}
            </div>
            <p className="text-xs text-slate-400 mt-1 font-mono">
              Accepted formats: JPG, JPEG, PNG, TIFF (512x512)
            </p>
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-3 rounded bg-rose-950/30 border border-rose-900/50 text-rose-300 text-xs font-mono flex items-start space-x-2.5">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
          <div>
            <span className="font-semibold text-rose-200 uppercase">Analysis Error: </span>
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Connected Service Status Notice */}
      <div className="p-3 rounded bg-emerald-950/20 border border-emerald-900/40 text-emerald-300 text-xs font-mono flex items-start space-x-2.5">
        <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-emerald-400" />
        <div>
          <span className="font-semibold text-emerald-200 uppercase">AI Service Active: </span>
          <span>
            {hasResult
              ? 'U-Net segmentation & road network graph extraction completed.'
              : 'FastAPI AI engine ready on GPU/CPU.'}
          </span>
        </div>
      </div>
    </div>
  );
};
