import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App, calculateInvoiceTotals, filterInvoices } from './main';
import type { Client, Invoice } from './main';

const authUser = {
  id: 1,
  email: 'demo@facnor.test',
  company_name: 'FacNor Demo',
  siren: '123456789',
  vat_number: 'FR00123456789',
  address: '1 rue de Paris',
};

const clients: Client[] = [
  {
    id: 10,
    name: 'Dupont SAS',
    email: 'contact@dupont.test',
    client_type: 'business',
    siren: '111222333',
    vat_number: 'FR111222333',
    address: '10 avenue République',
  },
  {
    id: 11,
    name: 'Élodie Martin',
    email: null,
    client_type: 'individual',
    siren: null,
    vat_number: null,
    address: '5 rue des Lilas',
  },
];

const invoices: Invoice[] = [
  {
    id: 100,
    number: 'FAC-2024-0001',
    issue_date: '2024-01-15',
    due_date: '2024-02-15',
    status: 'draft',
    client_id: 10,
    total_including_tax: '1200.00',
  },
  {
    id: 101,
    number: 'FAC-2024-0002',
    issue_date: '2024-01-20',
    due_date: null,
    status: 'sent',
    client_id: 11,
    total_including_tax: '240.00',
  },
];

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json', ...init.headers },
    ...init,
  });
}

function renderAuthenticatedApp(fetchMock = defaultDashboardFetch()) {
  localStorage.setItem('facnor.authToken', 'token-123');
  localStorage.setItem('facnor.authUser', JSON.stringify(authUser));
  vi.stubGlobal('fetch', fetchMock);
  render(<App />);
}

function defaultDashboardFetch() {
  return vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === '/api/clients') return jsonResponse(clients);
    if (path === '/api/invoices') return jsonResponse(invoices);
    throw new Error(`Unhandled request: ${path}`);
  });
}

beforeEach(() => {
  localStorage.clear();
  window.history.replaceState(null, '', '/');
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('App authentication', () => {
  it('logs in, stores the session and loads the dashboard', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === '/api/auth/login') {
        expect(init?.method).toBe('POST');
        expect(JSON.parse(String(init?.body))).toEqual({ email: 'demo@facnor.test', password: 'password123' });
        return jsonResponse({ access_token: 'token-123', token_type: 'bearer', user: authUser });
      }
      if (path === '/api/clients') return jsonResponse(clients);
      if (path === '/api/invoices') return jsonResponse(invoices);
      throw new Error(`Unhandled request: ${path}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App />);

    await userEvent.type(screen.getByLabelText(/adresse e-mail/i), 'demo@facnor.test');
    await userEvent.type(screen.getByLabelText(/mot de passe/i), 'password123');
    await userEvent.click(screen.getByRole('button', { name: /se connecter/i }));

    expect(await screen.findByRole('heading', { name: /bienvenue, facnor demo/i })).toBeInTheDocument();
    expect(localStorage.getItem('facnor.authToken')).toBe('token-123');
    expect(window.location.pathname).toBe('/dashboard');
    expect(await screen.findByRole('heading', { name: 'Dupont SAS' })).toBeInTheDocument();
    expect(await screen.findByText('FAC-2024-0001')).toBeInTheDocument();
  });

  it('displays an explicit error when credentials are rejected', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({ detail: 'Unauthorized' }, { status: 401 })));

    render(<App />);

    await userEvent.type(screen.getByLabelText(/adresse e-mail/i), 'demo@facnor.test');
    await userEvent.type(screen.getByLabelText(/mot de passe/i), 'wrongpass');
    await userEvent.click(screen.getByRole('button', { name: /se connecter/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Identifiants invalides.');
    expect(localStorage.getItem('facnor.authToken')).toBeNull();
  });
});

describe('Dashboard clients', () => {
  it('creates a client through the protected API and updates the list', async () => {
    const createdClient = {
      id: 12,
      name: 'Alpha Conseil',
      email: 'contact@alpha.test',
      client_type: 'business',
      siren: '987654321',
      vat_number: 'FR987654321',
      address: '7 place Bellecour',
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === '/api/clients' && !init?.method) return jsonResponse(clients);
      if (path === '/api/invoices') return jsonResponse(invoices);
      if (path === '/api/clients' && init?.method === 'POST') {
        expect(init.headers).toMatchObject({ Authorization: 'Bearer token-123' });
        expect(JSON.parse(String(init.body))).toEqual({
          name: 'Alpha Conseil',
          email: 'contact@alpha.test',
          client_type: 'business',
          siren: '987654321',
          vat_number: 'FR987654321',
          address: '7 place Bellecour',
        });
        return jsonResponse(createdClient, { status: 201 });
      }
      throw new Error(`Unhandled request: ${path}`);
    });

    renderAuthenticatedApp(fetchMock);
    await screen.findByRole('heading', { name: 'Dupont SAS' });

    await userEvent.type(screen.getByLabelText(/nom ou raison sociale/i), ' Alpha Conseil ');
    await userEvent.type(screen.getByLabelText(/^adresse e-mail$/i), 'contact@alpha.test');
    await userEvent.type(screen.getByLabelText(/^siren$/i), '987654321');
    await userEvent.type(screen.getByLabelText(/tva intracommunautaire/i), 'FR987654321');
    await userEvent.type(screen.getByLabelText(/adresse de facturation/i), ' 7 place Bellecour ');
    await userEvent.click(screen.getByRole('button', { name: /créer le client/i }));

    expect(await screen.findByRole('status')).toHaveTextContent('Client créé avec succès.');
    expect(screen.getByRole('heading', { name: 'Alpha Conseil' })).toBeInTheDocument();
  });
});

describe('Dashboard invoices', () => {
  it('calculates totals, creates an invoice and adds it to history', async () => {
    const createdInvoice = {
      id: 102,
      number: 'FAC-2024-0003',
      issue_date: '2024-03-01',
      due_date: '2024-03-31',
      status: 'draft',
      client_id: 10,
      total_including_tax: '360.00',
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === '/api/clients') return jsonResponse(clients);
      if (path === '/api/invoices' && !init?.method) return jsonResponse(invoices);
      if (path === '/api/invoices' && init?.method === 'POST') {
        expect(JSON.parse(String(init.body))).toEqual({
          client_id: 10,
          issue_date: expect.any(String),
          due_date: '2024-03-31',
          items: [
            {
              description: 'Prestation de conseil',
              quantity: '2.00',
              unit_price_excluding_tax: '150.00',
              vat_rate: '20.00',
            },
          ],
        });
        return jsonResponse(createdInvoice, { status: 201 });
      }
      throw new Error(`Unhandled request: ${path}`);
    });

    renderAuthenticatedApp(fetchMock);
    await screen.findByRole('heading', { name: 'FAC-2024-0001' });

    await userEvent.selectOptions(screen.getByLabelText(/client facturé/i), '10');
    await userEvent.type(screen.getByLabelText(/date d’échéance/i), '2024-03-31');
    await userEvent.type(screen.getByLabelText(/description/i), 'Prestation de conseil');
    const line = screen.getByRole('group', { name: /ligne 1/i });
    await userEvent.clear(within(line).getByLabelText(/qté/i));
    await userEvent.type(within(line).getByLabelText(/qté/i), '2');
    await userEvent.type(within(line).getByLabelText(/prix ht/i), '150');

    expect(screen.getAllByText(/360,00\s€/)[0]).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /créer la facture/i }));

    expect(await screen.findByRole('status')).toHaveTextContent('Facture FAC-2024-0003 créée avec succès.');
    expect(screen.getByText('FAC-2024-0003')).toBeInTheDocument();
  });

  it('filters invoices accent-insensitively and exports a PDF filename from headers', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === '/api/clients') return jsonResponse(clients);
      if (path === '/api/invoices') return jsonResponse(invoices);
      if (path === '/api/invoices/100/pdf') {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-123' });
        return new Response(new Blob(['pdf'], { type: 'application/pdf' }), {
          status: 200,
          headers: { 'Content-Disposition': 'attachment; filename="facture-dupont.pdf"' },
        });
      }
      throw new Error(`Unhandled request: ${path}`);
    });
    const createObjectURL = vi.fn(() => 'blob:test-url');
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);

    renderAuthenticatedApp(fetchMock);
    await screen.findByRole('heading', { name: 'FAC-2024-0001' });

    await userEvent.type(screen.getByLabelText(/rechercher par client ou siren/i), 'elodie');
    expect(screen.queryByText('FAC-2024-0001')).not.toBeInTheDocument();
    expect(screen.getByText('FAC-2024-0002')).toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText(/rechercher par client ou siren/i));
    await userEvent.type(screen.getByLabelText(/rechercher par client ou siren/i), '111222333');
    await userEvent.click(screen.getByRole('button', { name: /exporter pdf/i }));

    await waitFor(() => expect(createObjectURL).toHaveBeenCalled());
    expect(clickSpy).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:test-url');
    expect(await screen.findByRole('status')).toHaveTextContent('Export PDF de la facture FAC-2024-0001 téléchargé.');

    clickSpy.mockRestore();
  });
});

describe('frontend helpers', () => {
  it('calculates rounded invoice totals and filters by normalized client data', () => {
    expect(
      calculateInvoiceTotals([
        { id: 'a', description: 'A', quantity: '2', unit_price_excluding_tax: '10,005', vat_rate: '20' },
        { id: 'b', description: 'B', quantity: '1', unit_price_excluding_tax: '5', vat_rate: '5.5' },
      ]),
    ).toEqual({ total_excluding_tax: 25.01, total_tax: 4.28, total_including_tax: 29.29 });

    expect(filterInvoices(invoices, clients, 'elodie')).toEqual([invoices[1]]);
    expect(filterInvoices(invoices, clients, '111222333')).toEqual([invoices[0]]);
  });
});
