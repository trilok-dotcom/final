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
}

export const roadConditionService = {
  analyzeRoadCondition: async (params?: {
    pre_image_name?: string;
    post_image_name?: string;
    demo_scenario?: string;
  }): Promise<RoadConditionAssessment> => {
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
