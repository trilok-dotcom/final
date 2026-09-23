import { ApiClient } from './api';

export interface RoadSegment {
  edge_id: string;
  start_node: string;
  end_node: string;
  pre_length_m: number;
  post_length_m: number;
  preservation_ratio: number;
  pre_confidence: number;
  post_confidence: number;
  connectivity: 'CONNECTED' | 'PARTIAL' | 'BROKEN' | 'UNKNOWN';
  condition: 'SAFE' | 'DEGRADED' | 'BLOCKED' | 'UNKNOWN';
  condition_score: number;
  traversable: boolean;
  geometry: [number, number][]; // [lng, lat] GeoJSON coordinates
}

export interface RoadConditionAssessment {
  assessment_id: string;
  status: string;
  provider?: string;
  model?: string;
  road_count?: number;
  pre_image_path?: string;
  post_image_path?: string;
  roads_analyzed: number;
  safe_count: number;
  degraded_count: number;
  blocked_count: number;
  unknown_count: number;
  is_active: boolean;
  created_at: string;
  segments: RoadSegment[];
  roads?: RoadSegment[];
  road_mask_url?: string;
  before_mask_url?: string;
  change_mask_url?: string;
  condition_mask_url?: string;
  overlay_image_url?: string;
  annotated_after_image?: string;
  usability_overlay_url?: string;
  disclaimer?: string;
  georeferenced?: boolean;
  georeference_status?: string;
  comparison_available?: boolean;
  statistics?: {
    total_detected_road_pixels: number;
    detected_road_coverage_pct: number;
    uncertain_road_coverage_pct: number;
    changed_unavailable_coverage_pct: number;
    number_of_road_segments: number;
    average_road_confidence: number;
  };
  provider_configured?: boolean;
  average_confidence?: number;
  provider_name?: string;
  model_name?: string;
  summary?: {
    safe: number;
    degraded: number;
    blocked: number;
    unknown: number;
  };
}

export const roadConditionService = {
  analyzeRoadCondition: async (params?: {
    before_image?: File | null;
    after_image?: File | null;
    pre_image_name?: string;
    post_image_name?: string;
    demo_scenario?: string;
  }): Promise<RoadConditionAssessment> => {
    if (params?.before_image || params?.after_image) {
      const formData = new FormData();
      if (params.before_image) {
        formData.append('before_image', params.before_image);
      }
      if (params.after_image) {
        formData.append('after_image', params.after_image);
      }
      if (params.demo_scenario) {
        formData.append('demo_scenario', params.demo_scenario);
      }
      return ApiClient.postForm<RoadConditionAssessment>('/road-condition/analyze', formData);
    }

    return ApiClient.post<RoadConditionAssessment>(
      '/road-condition/analyze',
      params || { demo_scenario: 'SECTOR_4_FLOOD' }
    );
  },

  getActiveAssessment: async (): Promise<{ active: boolean; assessment?: RoadConditionAssessment }> => {
    return ApiClient.get<{ active: boolean; assessment?: RoadConditionAssessment }>('/road-condition/active');
  },

  getAssessment: async (assessmentId: string): Promise<RoadConditionAssessment> => {
    return ApiClient.get<RoadConditionAssessment>(`/road-condition/${assessmentId}`);
  },

  applyAssessment: async (assessmentId: string): Promise<{ success: boolean; message: string; active_assessment: RoadConditionAssessment }> => {
    return ApiClient.post<{ success: boolean; message: string; active_assessment: RoadConditionAssessment }>(
      `/road-condition/${assessmentId}/apply`,
      {}
    );
  },

  resetAssessment: async (): Promise<{ success: boolean; message: string }> => {
    return ApiClient.post<{ success: boolean; message: string }>('/road-condition/reset', {});
  },
};
