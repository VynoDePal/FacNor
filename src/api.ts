const DEFAULT_API_BASE_URL = 'http://localhost:8000';

export type HealthResponse = {
  status: string;
};

export function getApiBaseUrl(): string {
  return (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '');
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${getApiBaseUrl()}/health`);

  if (!response.ok) {
    throw new Error(`API FacNor indisponible (${response.status})`);
  }

  return response.json() as Promise<HealthResponse>;
}
