export type AuthResponse = {
  id?: number;
  email?: string;
  full_name?: string;
  access_token: string;
  token_type: string;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type RegisterPayload = LoginPayload & {
  full_name: string;
};

const DEFAULT_API_URL = 'http://localhost:8000';

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_URL).replace(/\/$/, '');

async function request<T>(path: string, options: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => undefined);
    const detail = typeof body?.detail === 'string' ? body.detail : 'Une erreur est survenue.';
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export function login(payload: LoginPayload): Promise<AuthResponse> {
  return request<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function register(payload: RegisterPayload): Promise<AuthResponse> {
  return request<AuthResponse>('/users', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
