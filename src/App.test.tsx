import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';

const apiMocks = vi.hoisted(() => ({
  login: vi.fn(),
  fetchCurrentUser: vi.fn(),
  fetchClients: vi.fn(),
  fetchInvoices: vi.fn(),
  createClient: vi.fn(),
  createInvoice: vi.fn(),
  downloadInvoicePdf: vi.fn(),
}));

vi.mock('./api', async () => {
  const actual = await vi.importActual<typeof import('./api')>('./api');
  return {
    ...actual,
    login: apiMocks.login,
    fetchCurrentUser: apiMocks.fetchCurrentUser,
    fetchClients: apiMocks.fetchClients,
    fetchInvoices: apiMocks.fetchInvoices,
    createClient: apiMocks.createClient,
    createInvoice: apiMocks.createInvoice,
    downloadInvoicePdf: apiMocks.downloadInvoicePdf,
  };
});

describe('App integration flow', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();

    apiMocks.login.mockResolvedValue({
      access_token: 'token-123',
      token_type: 'bearer',
      user_id: 1,
      user: { id: 1, email: 'demo@example.com', full_name: 'Demo User' },
    });
    apiMocks.fetchCurrentUser.mockResolvedValue({ id: 1, email: 'demo@example.com', full_name: 'Demo User' });
    apiMocks.fetchClients.mockResolvedValue([
      {
        id: 5,
        user_id: 1,
        name: 'Client SARL',
        email: 'client@example.com',
        address: '1 rue Exemple',
        postal_code: '75001',
        city: 'Paris',
        country: 'France',
        siren: '123456789',
        vat_number: 'FR123456789',
        created_at: '2025-01-01T00:00:00',
      },
    ]);
    apiMocks.fetchInvoices.mockResolvedValue([
      {
        id: 7,
        user_id: 1,
        client_id: 5,
        sequence_number: 1,
        invoice_number: 'FAC-000001',
        issue_date: '2025-01-01',
        due_date: '2025-01-31',
        status: 'issued',
        currency: 'EUR',
        total_excluding_tax: 10000,
        total_tax: 2000,
        total_including_tax: 12000,
        created_at: '2025-01-01T00:00:00',
        lines: [
          {
            id: 1,
            invoice_id: 7,
            line_order: 1,
            description: 'Prestation',
            quantity: 1,
            unit_price_excluding_tax: 10000,
            vat_rate: 20,
            total_excluding_tax: 10000,
            total_tax: 2000,
            total_including_tax: 12000,
          },
        ],
      },
    ]);
    apiMocks.downloadInvoicePdf.mockResolvedValue('facture-FAC-000001.pdf');
  });

  it('logs in, loads dashboard data, and downloads an invoice PDF', async () => {
    render(<App />);

    await userEvent.type(screen.getByRole('textbox'), 'demo@example.com');
    await userEvent.type(screen.getByLabelText(/mot de passe/i), 'secret');
    await userEvent.click(screen.getByRole('button', { name: /se connecter/i }));

    expect(await screen.findByRole('heading', { name: /bienvenue, demo user/i })).toBeInTheDocument();
    expect(await screen.findByText('FAC-000001')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /télécharger le pdf/i }));

    await waitFor(() => {
      expect(screen.getByText(/téléchargement de facture-fac-000001\.pdf lancé\./i)).toBeInTheDocument();
    });
    expect(apiMocks.login).toHaveBeenCalledWith('demo@example.com', 'secret');
    expect(apiMocks.fetchClients).toHaveBeenCalledWith('token-123');
    expect(apiMocks.fetchInvoices).toHaveBeenCalledWith('token-123');
    expect(apiMocks.downloadInvoicePdf).toHaveBeenCalledWith('token-123', expect.objectContaining({ id: 7, invoice_number: 'FAC-000001' }));
  });
});
