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


export type InvoiceLinePayload = {
  description: string;
  quantity: number;
  unit_price_excluding_tax: number;
  vat_rate: number;
};

export type InvoicePayload = {
  client_id: number;
  issue_date?: string | null;
  due_date?: string | null;
  lines: InvoiceLinePayload[];
};

export type InvoiceLine = InvoiceLinePayload & {
  id: number;
  invoice_id: number;
  line_order: number;
  total_excluding_tax: number;
  total_tax: number;
  total_including_tax: number;
};

export type Invoice = {
  id: number;
  user_id: number;
  client_id: number;
  sequence_number: number;
  invoice_number: string;
  issue_date: string;
  due_date?: string | null;
  status: 'draft' | 'issued' | 'paid' | 'cancelled';
  currency: string;
  total_excluding_tax: number;
  total_tax: number;
  total_including_tax: number;
  created_at: string;
  lines: InvoiceLine[];
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

export async function fetchInvoices(token: string): Promise<Invoice[]> {
  return request<Invoice[]>('/invoices', {
    headers: authHeaders(token),
  });
}

export async function createInvoice(token: string, payload: InvoicePayload): Promise<Invoice> {
  return request<Invoice>('/invoices', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
    body: JSON.stringify(payload),
  });
}
