export type PriorityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type UrgencyLevel = 'IMMEDIATE' | 'URGENT' | 'PRIORITY' | 'ROUTINE';
export type RiskLevel = 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';

export interface ResourceRecommendation {
  unit_type: string;
  quantity: number;
  reason: string;
}

export interface ScoringFactor {
  name: string;
  raw_score: number;
  weight: number;
  weighted_score: number;
  reason: string;
}

export interface IncidentIntelligence {
  incident_id: string;
  incident_code?: string;
  priority_score: number;
  priority: PriorityLevel | string;
  risk_level: RiskLevel | string;
  urgency: UrgencyLevel | string;
  recommended_resources: ResourceRecommendation[];
  factors: ScoringFactor[];
  explanation: string;
  analyzed_at: string;
}
