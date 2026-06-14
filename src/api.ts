const DEFAULT_API_BASE_URL = 'http://localhost:8000';

export type HealthResponse = {
  status: string;
};

export type User = {
  id: number;
  email: string;
  full_name: string | null;
};

export type AuthResponse = {
  access_token: string;
  token_type: 'bearer';
  user: User;
};

export type LoginCredentials = {
  email: string;
  password: string;
};

export function getApiBaseUrl(): string {
  return (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '');
}

async function parseApiError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string | Array<{ msg?: string }> };
    if (typeof payload.detail === 'string') {
      return payload.detail;
    }
    if (Array.isArray(payload.detail) && payload.detail[0]?.msg) {
      return payload.detail[0].msg;
    }
  } catch {
    // Fall back to the generic message below.
  }

  return `Erreur API FacNor (${response.status})`;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${getApiBaseUrl()}/health`);

  if (!response.ok) {
    throw new Error(`API FacNor indisponible (${response.status})`);
  }

  return response.json() as Promise<HealthResponse>;
}

export async function login(credentials: LoginCredentials): Promise<AuthResponse> {
  const response = await fetch(`${getApiBaseUrl()}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }

  return response.json() as Promise<AuthResponse>;
}
