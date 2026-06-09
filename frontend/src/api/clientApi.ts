import { Client, ClientCreate, ClientUpdate } from '../types/client';

const API_BASE_URL = 'http://localhost:8000';

export const clientService = {
  async getAllClients(): Promise<Client[]> {
    const response = await fetch(`${API_BASE_URL}/clients/`);
    if (!response.ok) throw new Error('Failed to fetch clients');
    return response.json();
  },

  async getClient(id: number): Promise<Client> {
    const response = await fetch(`${API_BASE_URL}/clients/${id}`);
    if (!response.ok) throw new Error('Failed to fetch client');
    return response.json();
  },

  async createClient(client: ClientCreate): Promise<Client> {
    const response = await fetch(`${API_BASE_URL}/clients/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(client),
    });
    if (!response.ok) throw new Error('Failed to create client');
    return response.json();
  },

  async updateClient(id: number, client: ClientUpdate): Promise<Client> {
    const response = await fetch(`${API_BASE_URL}/clients/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(client),
    });
    if (!response.ok) throw new Error('Failed to update client');
    return response.json();
  },

  async deleteClient(id: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/clients/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete client');
  },
};
