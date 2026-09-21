export interface EvaluationMetric {
  id: string;
  evaluation_run_id?: string;
  metric_name: string;
  metric_value: number | null;
  unit: string | null;
  category: string;
  metadata?: Record<string, any>;
}

export interface EvaluationRun {
  id: string;
  evaluation_type: string;
  dataset_version: string | null;
  model_version: string | null;
  simulation_id: string | null;
  baseline_type: string | null;
  sample_count: number;
  started_at: string;
  completed_at: string | null;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  metadata: Record<string, any>;
  metrics?: EvaluationMetric[];
}

export interface ThresholdCurvePoint {
  threshold: number;
  dice: number;
  iou: number;
  precision: number;
  recall: number;
  accuracy: number;
}

export interface InferenceLatencyStats {
  device: string;
  model: string;
  image_size: string;
  batch_size: number;
  sample_count: number;
  preprocess_mean_ms: number;
  inference_mean_ms: number;
  inference_median_ms: number;
  inference_min_ms: number;
  inference_max_ms: number;
  inference_std_ms: number;
  postprocess_mean_ms: number;
  total_pipeline_mean_ms: number;
}

export interface EvaluationOverview {
  success: boolean;
  generated_at: string;
  system_info: {
    model_version: string;
    dataset_version: string;
    production_threshold: number;
  };
  ai: {
    status: string;
    model_version?: string;
    threshold?: number;
    dice?: number | null;
    iou?: number | null;
    precision?: number | null;
    recall?: number | null;
    inference_ms?: number | null;
    best_threshold?: number | null;
    best_dice?: number | null;
  };
  routing: {
    status: string;
    routes_evaluated?: number | null;
    success_rate?: number | null;
    average_distance_m?: number | null;
    average_eta_s?: number | null;
    average_confidence?: number | null;
    average_route_health?: number | null;
  };
  resources: {
    status: string;
    total_units?: number | null;
    utilization_percent?: number | null;
    optimization_runs?: number | null;
    average_optimization_score?: number | null;
  };
  missions: {
    status: string;
    total_dispatches?: number | null;
    completed?: number | null;
    average_dispatch_latency_s?: number | null;
    average_duration_s?: number | null;
  };
  rerouting: {
    status: string;
    degradation_events?: number | null;
    recommendations?: number | null;
    approved?: number | null;
    average_health_improvement?: number | null;
    average_eta_change_s?: number | null;
  };
  simulation: {
    status: string;
    sessions_evaluated?: number;
  };
  baselines: {
    osrm_baseline?: Record<string, any> | null;
    nearest_unit_baseline?: Record<string, any> | null;
  };
}
