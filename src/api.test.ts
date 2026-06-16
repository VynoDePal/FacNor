import { afterEach, describe, expect, it, vi } from 'vitest';
import { API_BASE_URL, createClient, downloadInvoicePdf, login } from './api';

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
    ...init,
  });
}

describe('frontend API client', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('uses the configured backend base URL for authentication', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({
      access_token: 'token-123',
      token_type: 'bearer',
      user_id: 1,
      user: { id: 1, email: 'demo@example.com', full_name: 'Demo User' },
    }));

    const auth = await login('demo@example.com', 'secret');

    expect(auth.access_token).toBe('token-123');
    expect(fetchMock).toHaveBeenCalledWith(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'demo@example.com', password: 'secret' }),
    });
  });

  it('sends authenticated JSON requests when creating clients', async () => {
    const payload = {
      name: 'Client SARL',
      email: 'client@example.com',
      address: '1 rue Exemple',
      postal_code: '75001',
      city: 'Paris',
      country: 'France',
      siren: '123456789',
      vat_number: 'FR123456789',
    };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({
      id: 42,
      user_id: 1,
      created_at: '2025-01-01T00:00:00',
      ...payload,
    }));

    const client = await createClient('token-123', payload);

    expect(client.id).toBe(42);
    expect(fetchMock).toHaveBeenCalledWith(`${API_BASE_URL}/clients`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer token-123' },
      body: JSON.stringify(payload),
    });
  });

  it('downloads invoice PDFs with the filename returned by the backend', async () => {
    const click = vi.fn();
    const remove = vi.fn();
    const appendChild = vi.spyOn(document.body, 'appendChild').mockImplementation(((node: Node) => node) as typeof document.body.appendChild);
    const originalCreateElement = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation(((tagName: string) => {
      if (tagName === 'a') {
        return {
          click,
          remove,
          href: '',
          download: '',
        } as unknown as HTMLAnchorElement;
      }
      return originalCreateElement(tagName);
    }) as typeof document.createElement);
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:invoice'),
      revokeObjectURL: vi.fn(),
    });
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-disposition': "attachment; filename*=UTF-8''facture-FAC-000001.pdf" }),
      blob: vi.fn().mockResolvedValue(new Blob(['%PDF-1.4'], { type: 'application/pdf' })),
    } as unknown as Response);

    const filename = await downloadInvoicePdf('token-123', { id: 7, invoice_number: 'FAC-000001' });

    expect(filename).toBe('facture-FAC-000001.pdf');
    expect(fetchMock).toHaveBeenCalledWith(`${API_BASE_URL}/invoices/7/pdf`, {
      headers: { Authorization: 'Bearer token-123' },
    });
    expect(appendChild).toHaveBeenCalled();
    expect(click).toHaveBeenCalledOnce();
    expect(remove).toHaveBeenCalledOnce();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:invoice');
  });
});
