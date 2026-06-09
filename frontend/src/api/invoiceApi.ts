import { Invoice, InvoiceCreate } from '../types/invoice';

const API_BASE_URL = '/api'; // This might need to be adjusted based on the vite config or actual API URL

export const invoiceService = {
  async createInvoice(invoice: InvoiceCreate): Promise<Invoice> {
    const response = await fetch(`${API_BASE_URL}/invoices/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(invoice),
    });

    if (!response.ok) {
      throw new Error('Erreur lors de la création de la facture');
    }

    return response.json();
  },

  async getInvoice(id: number): Promise<Invoice> {
    const response = await fetch(`${API_BASE_URL}/invoices/${id}`);
    if (!response.ok) {
      throw new Error('Erreur lors de la récupération de la facture');
    }
    return response.json();
  },

  async getAllInvoices(params: Record<string, any> = {}): Promise<Invoice[]> {
    const queryString = new URLSearchParams(params).toString();
    const response = await fetch(`${API_BASE_URL}/invoices/?${queryString}`);
    if (!response.ok) {
      throw new Error('Erreur lors de la récupération des factures');
    }
    return response.json();
  },
};
