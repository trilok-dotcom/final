/**
 * RESQROUTE API Client Service (Stage 2 Connected)
 * 
 * Communicates with FastAPI backend running on http://localhost:8000/api/v1
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export class ApiClient {
  static async get<T>(endpoint: string): Promise<T> {
    const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `API request failed with status ${response.status}`);
      }

      return (await response.json()) as T;
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('Network error connecting to RESQROUTE backend API.');
    }
  }

  static async post<T>(endpoint: string, payload: unknown): Promise<T> {
    const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `API request failed with status ${response.status}`);
      }

      return (await response.json()) as T;
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('Network error connecting to RESQROUTE backend API.');
    }
  }
}

export { API_BASE_URL };
