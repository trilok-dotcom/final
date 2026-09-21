export type AnalysisStage = 'idle' | 'uploading' | 'processing' | 'completed' | 'failed';

export interface AIPredictionResult {
  confidence: number;
  road_percentage: number;
  mask_url: string;
  overlay_url: string;
  heatmap_url: string;
}

export interface AIRoadNetworkResult {
  road_pixels: number;
  graph_nodes: number;
  graph_edges: number;
  coverage_percentage: number;
  connected_components: number;
  largest_component_nodes: number;
  skeleton_url: string;
  overlay_url: string;
  comparison_url?: string;
  geojson_url: string;
}

export interface AnalyzeSatelliteResponse {
  success: boolean;
  prediction: AIPredictionResult;
  road_network: AIRoadNetworkResult;
}

export interface SatelliteAnalysisRequest {
  imageId: string;
  filename: string;
  fileSize: number;
}

export interface SatelliteAnalysisResponse {
  id: string;
  originalImageUrl: string;
  roadMaskUrl?: string;
  roadNetworkUrl?: string;
  overlayUrl?: string;
  confidenceScore: number;
  extractedRoadMeters: number;
  processedAt: string;
  status: AnalysisStage;
  message?: string;
}

export type AIAnalysisResult = SatelliteAnalysisResponse;
