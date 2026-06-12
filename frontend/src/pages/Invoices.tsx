import React, { useEffect, useState } from 'react';
import api from '../api/apiClient';
import type { Invoice, InvoiceItem } from '../types';

const Invoices = () => {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [clientId, setClientId] = useState('');
  const [items, setItems] = useState<InvoiceItem[]>([{ description: '', quantity: 1, unit_price: 0, tva_rate: 20 }]);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchInvoices();
  }, []);

  const fetchInvoices = async () => {
    try {
      const response = await api.get('/invoices/');
      setInvoices(response.data);
    } catch (err: any) {
      setError('Failed to fetch invoices');
    }
  };

  const addItem = () => setItems([...items, { description: '', quantity: 1, unit_price: 0, tva_rate: 20 }]);
  const updateItem = (index: number, field: keyof InvoiceItem, value: any) => {
    const newItems = [...items];
    newItems[index] = { ...newItems[index], [field]: value };
    setItems(newItems);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/invoices/', { client_id: parseInt(clientId), items });
      setItems([{ description: '', quantity: 1, unit_price: 0, tva_rate: 20 }]);
      setClientId('');
      fetchInvoices();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create invoice');
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <h2>Invoices</h2>
      <form onSubmit={handleSubmit} style={{ marginBottom: '20px' }}>
        <input placeholder="Client ID" value={clientId} onChange={e => setClientId(e.target.value)} required />
        <div style={{ margin: '10px 0' }}>
          <h4>Items</h4>
          {items.map((item, index) => (
            <div key={index} style={{ marginBottom: '5px' }}>
              <input placeholder="Description" value={item.description} onChange={e => updateItem(index, 'description', e.target.value)} required />
              <input type="number" placeholder="Qty" value={item.quantity} onChange={e => updateItem(index, 'quantity', parseFloat(e.target.value))} required />
              <input type="number" placeholder="Price" value={item.unit_price} onChange={e => updateItem(index, 'unit_price', parseFloat(e.target.value))} required />
              <input type="number" placeholder="TVA %" value={item.tva_rate} onChange={e => updateItem(index, 'tva_rate', parseFloat(e.target.value))} required />
            </div>
          ))}
          <button type="button" onClick={addItem}>Add Item</button>
        </div>
        <button type="submit">Create Invoice</button>
      </form>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <ul>
        {invoices.map(i => (
          <li key={i.id}>Invoice #{i.number} - Client {i.client_id} - Total TTC: {i.total_ttc}€</li>
        ))}
      </ul>
    </div>
  );
};

export default Invoices;
