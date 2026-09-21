import { API_BASE_URL } from './api';
import type { AnalyzeSatelliteResponse } from '../types/ai';

/**
 * Upload satellite image and run full U-Net segmentation + Road Network Graph extraction pipeline.
 */
export async function uploadSatelliteImage(file: File): Promise<AnalyzeSatelliteResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/analyze-satellite`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Satellite image analysis failed with status ${response.status}`);
  }

  return (await response.json()) as AnalyzeSatelliteResponse;
}
