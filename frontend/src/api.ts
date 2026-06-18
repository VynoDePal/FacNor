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

export type Client = {
  id: number;
  user_id: number;
  client_type: 'b2b' | 'b2c';
  name: string;
  email: string | null;
  address: string;
  siren: string | null;
  vat_number: string | null;
  created_at: string;
};

export type ClientPayload = {
  client_type: 'b2b' | 'b2c';
  name: string;
  email?: string | null;
  address: string;
  siren?: string | null;
  vat_number?: string | null;
};

export type InvoiceLinePayload = {
  description: string;
  quantity: number;
  unit_price: number;
  tax_rate: number;
};

export type InvoicePayload = {
  client_id: number;
  invoice_number?: string | null;
  issue_date: string;
  due_date?: string | null;
  lines: InvoiceLinePayload[];
};

export type InvoiceLine = InvoiceLinePayload & {
  id: number;
  invoice_id: number;
  line_total_excluding_tax: number;
  line_total_tax: number;
  line_total_including_tax: number;
};

export type Invoice = {
  id: number;
  user_id: number;
  client_id: number;
  client_name?: string;
  invoice_number: string;
  issue_date: string;
  due_date: string | null;
  status: 'draft' | 'issued' | 'paid' | 'cancelled';
  currency: string;
  total_excluding_tax: number;
  total_tax: number;
  total_including_tax: number;
  created_at: string;
  lines?: InvoiceLine[];
};

export type InvoiceFilters = {
  search?: string;
  status_filter?: Invoice['status'] | '';
  client_id?: number | '';
  issue_date_from?: string;
  issue_date_to?: string;
};

export type HealthResponse = {
  status: string;
};

const DEFAULT_API_URL = 'http://localhost:8000';

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_URL).replace(/\/$/, '');

function formatErrorDetail(detail: unknown): string {
  if (typeof detail === 'string') {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item?.msg === 'string') {
          return item.msg;
        }
        if (typeof item === 'string') {
          return item;
        }
        return undefined;
      })
      .filter(Boolean)
      .join(' ');
  }
  return '';
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => undefined);
    const detail = formatErrorDetail(body?.detail) || 'Une erreur est survenue.';
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health', { method: 'GET' });
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

export function listClients(token: string): Promise<Client[]> {
  return request<Client[]>('/clients', {
    method: 'GET',
    headers: authHeaders(token),
  });
}

export function createClient(token: string, payload: ClientPayload): Promise<Client> {
  return request<Client>('/clients', {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export function updateClient(token: string, clientId: number, payload: ClientPayload): Promise<Client> {
  return request<Client>(`/clients/${clientId}`, {
    method: 'PUT',
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export function deleteClient(token: string, clientId: number): Promise<void> {
  return request<void>(`/clients/${clientId}`, {
    method: 'DELETE',
    headers: authHeaders(token),
  });
}

function buildQueryString(filters: InvoiceFilters = {}): string {
  const parameters = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      parameters.set(key, String(value));
    }
  });
  const queryString = parameters.toString();
  return queryString ? `?${queryString}` : '';
}

export function listInvoices(token: string, filters: InvoiceFilters = {}): Promise<Invoice[]> {
  return request<Invoice[]>(`/invoices${buildQueryString(filters)}`, {
    method: 'GET',
    headers: authHeaders(token),
  });
}

export function createInvoice(token: string, payload: InvoicePayload): Promise<Invoice> {
  return request<Invoice>('/invoices', {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}
