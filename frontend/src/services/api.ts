import axios from 'axios';

const API_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
});

// Add a request interceptor to include the token if it's available in localStorage
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export const clientService = {
  getAll: async () => {
    const response = await api.get('/clients/');
    return response.data;
  },
  getById: async (id: number) => {
    const response = await api.get(`/clients/${id}`);
    return response.data;
  },
  create: async (clientData: any) => {
    const response = await api.post('/clients/', clientData);
    return response.data;
  },
  update: async (id: number, clientData: any) => {
    const response = await api.put(`/clients/${id}`, clientData);
    return response.data;
  },
  delete: async (id: number) => {
    await api.delete(`/clients/${id}`);
  },
};

export default api;
