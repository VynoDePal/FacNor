import React, { useEffect, useState } from 'react';
import api from '../api/apiClient';
import type { Client } from '../types';

const Clients = () => {
  const [clients, setClients] = useState<Client[]>([]);
  const [formData, setFormData] = useState({ 
    name: '', 
    email: '', 
    address: '', 
    phone: '', 
    siren: '', 
    tva_number: '', 
    is_company: false 
  });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchClients();
  }, []);

  const fetchClients = async () => {
    try {
      const response = await api.get('/clients/');
      setClients(response.data);
      setError('');
    } catch (err: any) {
      setError('Failed to fetch clients');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await api.put(`/clients/${editingId}/`, formData);
        setEditingId(null);
      } else {
        await api.post('/clients/', formData);
      }
      setFormData({ name: '', email: '', address: '', phone: '', siren: '', tva_number: '', is_company: false });
      fetchClients();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'An error occurred while saving the client');
    }
  };

  const handleEdit = (client: Client) => {
    setEditingId(client.id);
    setFormData({
      name: client.name,
      email: client.email,
      address: client.address,
      phone: client.phone,
      siren: client.siren,
      tva_number: client.tva_number,
      is_company: client.is_company,
    });
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this client?')) return;
    try {
      await api.delete(`/clients/${id}/`);
      fetchClients();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete client');
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <h2>{editingId ? 'Edit Client' : 'Clients'}</h2>
      <form onSubmit={handleSubmit} style={{ marginBottom: '20px', display: 'flex', flexDirection: 'column', gap: '10px', maxWidth: '400px' }}>
        <input placeholder="Name" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} required />
        <input placeholder="Email" type="email" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} />
        <input placeholder="Address" value={formData.address} onChange={e => setFormData({...formData, address: e.target.value})} />
        <input placeholder="Phone" value={formData.phone} onChange={e => setFormData({...formData, phone: e.target.value})} />
        <input placeholder="SIREN" value={formData.siren} onChange={e => setFormData({...formData, siren: e.target.value})} />
        <input placeholder="TVA Number" value={formData.tva_number} onChange={e => setFormData({...formData, tva_number: e.target.value})} />
        <label>
          <input type="checkbox" checked={formData.is_company} onChange={e => setFormData({...formData, is_company: e.target.checked})} />
          Is Company
        </label>
        <button type="submit">{editingId ? 'Update Client' : 'Add Client'}</button>
        {editingId && <button type="button" onClick={() => { setEditingId(null); setFormData({ name: '', email: '', address: '', phone: '', siren: '', tva_number: '', is_company: false }); }}>Cancel</button>}
      </form>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ textAlign: 'left', borderBottom: '1px solid #ccc' }}>
            <th>Name</th>
            <th>Email</th>
            <th>SIREN</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {clients.map(c => (
            <tr key={c.id} style={{ borderBottom: '1px solid #eee' }}>
              <td>{c.name}</td>
              <td>{c.email}</td>
              <td>{c.siren}</td>
              <td>
                <button onClick={() => handleEdit(c)}>Edit</button>
                <button onClick={() => handleDelete(c.id)} style={{ marginLeft: '10px', color: 'red' }}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default Clients;
