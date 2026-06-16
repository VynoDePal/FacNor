const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export type AuthUser = {
  id: number;
  email: string;
  full_name: string;
  company_name?: string | null;
};

export type AuthResponse = {
  access_token: string;
  token_type: 'bearer';
  user_id: number;
  user: AuthUser;
};

export type Client = {
  id: number;
  user_id: number;
  name: string;
  email?: string | null;
  address: string;
  postal_code: string;
  city: string;
  country: string;
  siren?: string | null;
  vat_number?: string | null;
  created_at: string;
};

export type ClientPayload = {
  name: string;
  email?: string | null;
  address: string;
  postal_code: string;
  city: string;
  country: string;
  siren?: string | null;
  vat_number?: string | null;
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, options);

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? 'Requête impossible');
  }

  return response.json();
}

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
}

export async function fetchCurrentUser(token: string): Promise<AuthUser> {
  return request<AuthUser>('/auth/me', {
    headers: authHeaders(token),
  });
}

export async function fetchClients(token: string): Promise<Client[]> {
  return request<Client[]>('/clients', {
    headers: authHeaders(token),
  });
}

export async function createClient(token: string, payload: ClientPayload): Promise<Client> {
  return request<Client>('/clients', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
    body: JSON.stringify(payload),
  });
}

export async function updateClient(token: string, clientId: number, payload: ClientPayload): Promise<Client> {
  return request<Client>(`/clients/${clientId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
    body: JSON.stringify(payload),
  });
}
