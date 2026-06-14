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

export type ClientType = 'individual' | 'company';

export type Client = {
  id: number;
  user_id: number;
  name: string;
  client_type: ClientType;
  email: string | null;
  address: string | null;
  siren: string | null;
  vat_number: string | null;
  created_at: string;
};

export type ClientPayload = {
  name: string;
  client_type: ClientType;
  email?: string | null;
  address?: string | null;
  siren?: string | null;
  vat_number?: string | null;
};

export type InvoiceStatus = 'draft' | 'issued' | 'paid' | 'cancelled';

export type InvoiceItem = {
  id: number;
  description: string;
  quantity: string;
  unit_price_excluding_tax: string;
  vat_rate: string;
  line_total_excluding_tax: string;
  line_total_vat: string;
  line_total_including_tax: string;
  created_at: string;
};

export type InvoiceItemPayload = {
  description: string;
  quantity: string;
  unit_price_excluding_tax: string;
  vat_rate: string;
};

export type Invoice = {
  id: number;
  user_id: number;
  client_id: number;
  invoice_number: string;
  issue_date: string;
  due_date: string | null;
  status: InvoiceStatus;
  total_excluding_tax: string;
  total_vat: string;
  total_including_tax: string;
  created_at: string;
  items: InvoiceItem[];
};

export type InvoicePayload = {
  client_id: number;
  issue_date: string;
  due_date?: string | null;
  status: InvoiceStatus;
  items: InvoiceItemPayload[];
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

async function requestApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }

  return response.json() as Promise<T>;
}

function authorizationHeader(token: string): { Authorization: string } {
  return { Authorization: `Bearer ${token}` };
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

export async function fetchClients(token: string): Promise<Client[]> {
  return requestApi<Client[]>('/clients', {
    headers: authorizationHeader(token),
  });
}

export async function createClient(token: string, payload: ClientPayload): Promise<Client> {
  return requestApi<Client>('/clients', {
    method: 'POST',
    headers: authorizationHeader(token),
    body: JSON.stringify(payload),
  });
}

export async function updateClient(token: string, clientId: number, payload: ClientPayload): Promise<Client> {
  return requestApi<Client>(`/clients/${clientId}`, {
    method: 'PUT',
    headers: authorizationHeader(token),
    body: JSON.stringify(payload),
  });
}

export async function fetchInvoices(token: string): Promise<Invoice[]> {
  return requestApi<Invoice[]>('/invoices', {
    headers: authorizationHeader(token),
  });
}

export async function createInvoice(token: string, payload: InvoicePayload): Promise<Invoice> {
  return requestApi<Invoice>('/invoices', {
    method: 'POST',
    headers: authorizationHeader(token),
    body: JSON.stringify(payload),
  });
}
