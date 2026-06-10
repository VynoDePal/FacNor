import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000'; // Adjust based on actual backend URL

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const clientService = {
  getAllClients: () => apiClient.get('/clients/'),
  getClientById: (id) => apiClient.get(`/clients/${id}`),
  createClient: (clientData) => apiClient.post('/clients/', clientData),
  updateClient: (id, clientData) => apiClient.put(`/clients/${id}`, clientData),
  deleteClient: (id) => apiClient.delete(`/clients/${id}`),
};
