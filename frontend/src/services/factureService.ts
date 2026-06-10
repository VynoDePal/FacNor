import axios from 'axios';
import { Facture, FactureCreate, FactureUpdate } from '../types/facture';

const API_BASE_URL = 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const factureService = {
  getFactures: (params = {}) => apiClient.get('/factures/', { params }),
  getFactureById: (id) => apiClient.get(`/factures/${id}`),
  createFacture: (factureData) => apiClient.post('/factures/', factureData),
  updateFacture: (id, factureData) => apiClient.put(`/factures/${id}`, factureData),
  deleteFacture: (id) => apiClient.delete(`/factures/${id}`),
};
