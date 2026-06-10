import React, { useState, useEffect } from 'react';
import { factureService } from '../services/factureService';
import { clientService } from '../services/clientService';
import { Facture } from '../types/facture';

const InvoiceList = () => {
  const [factures, setFactures] = useState<Facture[]>([]);
  const [clients, setClients] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [filters, setFilters] = useState({
    clientId: '',
    dateStart: '',
    dateEnd: '',
  });

  useEffect(() => {
    fetchClients();
    fetchFactures();
  }, []);

  useEffect(() => {
    fetchFactures();
  }, [filters]);

  const fetchClients = async () => {
    try {
      const response = await clientService.getAllClients();
      setClients(response.data);
    } catch (err) {
      console.error('Failed to fetch clients for filter', err);
    }
  };

  const fetchFactures = async () => {
    try {
      setLoading(true);
      const params = {
        client_id: filters.clientId || undefined,
        date_start: filters.dateStart || undefined,
        date_end: filters.dateEnd || undefined,
      };
      const response = await factureService.getFactures(params);
      setFactures(response.data);
    } catch (err) {
      setError('Failed to fetch invoices');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFilters(prev => ({ ...prev, [name]: value }));
  };

  const handleDelete = async (id: number) => {
    if (window.confirm('Are you sure you want to delete this invoice?')) {
      try {
        await factureService.deleteFacture(id);
        setFactures(factures.filter(f => f.id !== id));
      } catch (err) {
        alert('Failed to delete invoice');
        console.error(err);
      }
    }
  };

  if (loading && factures.length === 0) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h1>Factures</h1>
      <div style={{ marginBottom: '20px', display: 'flex', gap: '10px', alignItems: 'center' }}>
        <a href="/factures/new">Add New Invoice</a>
        
        <div style={{ marginLeft: '20px', display: 'flex', gap: '10px', alignItems: 'center' }}>
          <label>Client: </label>
          <select name="clientId" value={filters.clientId} onChange={handleFilterChange}>
            <option value="">All Clients</option>
            {clients.map(client => (
              <option key={client.id} value={client.id}>{client.name}</option>
            ))}
          </select>

          <label>From: </label>
          <input 
            type="date" 
            name="dateStart" 
            value={filters.dateStart} 
            onChange={handleFilterChange} 
          />

          <label>To: </label>
          <input 
            type="date" 
            name="dateEnd" 
            value={filters.dateEnd} 
            onChange={handleFilterChange} 
          />
        </div>
      </div>

      <table border="1" style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Number</th>
            <th>Client ID</th>
            <th>Date</th>
            <th>Due Date</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {factures.map(f => (
            <tr key={f.id}>
              <td>{f.id}</td>
              <td>{f.numero}</td>
              <td>{f.client_id}</td>
              <td>{f.date_facture}</td>
              <td>{f.date_echeance}</td>
              <td>{f.statut}</td>
              <td>
                <a href={`/factures/edit/${f.id}`}>Edit</a>
                <button onClick={() => handleDelete(f.id)} style={{ marginLeft: '10px' }}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default InvoiceList;
