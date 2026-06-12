import React, { useEffect, useState } from 'react';
import api from '../api/apiClient';
import type { Client } from '../types';

const Clients = () => {
  const [clients, setClients] = useState<Client[]>([]);
  const [formData, setFormData] = useState({ name: '', email: '', address: '', phone: '', tax_id: '' });
  const [error, setError] = useState('');

  useEffect(() => {
    fetchClients();
  }, []);

  const fetchClients = async () => {
    try {
      const response = await api.get('/clients/');
      setClients(response.data);
    } catch (err: any) {
      setError('Failed to fetch clients');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/clients/', formData);
      setFormData({ name: '', email: '', address: '', phone: '', tax_id: '' });
      fetchClients();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create client');
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <h2>Clients</h2>
      <form onSubmit={handleSubmit} style={{ marginBottom: '20px' }}>
        <input placeholder="Name" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} required />
        <input placeholder="Email" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} required />
        <input placeholder="Address" value={formData.address} onChange={e => setFormData({...formData, address: e.target.value})} required />
        <input placeholder="Phone" value={formData.phone} onChange={e => setFormData({...formData, phone: e.target.value})} required />
        <input placeholder="Tax ID" value={formData.tax_id} onChange={e => setFormData({...formData, tax_id: e.target.value})} required />
        <button type="submit">Add Client</button>
      </form>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <ul>
        {clients.map(c => (
          <li key={c.id}>{c.name} - {c.email} ({c.tax_id})</li>
        ))}
      </ul>
    </div>
  );
};

export default Clients;
