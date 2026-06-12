import React, { useEffect, useState } from 'react';
import api from '../api/apiClient';
import type { Invoice, InvoiceLine, Client } from '../types';

const Invoices = () => {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [clientId, setClientId] = useState('');
  const [lines, setLines] = useState<InvoiceLine[]>([{ description: '', quantity: 1, unit_price_ht: 0, vat_rate: 20 }]);
  const [dateIssued, setDateIssued] = useState(new Date().toISOString().split('T')[0]);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchInvoices();
    fetchClients();
  }, []);

  const fetchInvoices = async () => {
    try {
      const response = await api.get('/invoices/');
      setInvoices(response.data);
    } catch (err: any) {
      setError('Failed to fetch invoices');
    }
  };

  const fetchClients = async () => {
    try {
      const response = await api.get('/clients/');
      setClients(response.data);
    } catch (err: any) {
      setError('Failed to fetch clients');
    }
  };

  const addLine = () => setLines([...lines, { description: '', quantity: 1, unit_price_ht: 0, vat_rate: 20 }]);
  const removeLine = (index: number) => {
    const newLines = [...lines];
    newLines.splice(index, 1);
    setLines(newLines);
  };
  const updateLine = (index: number, field: keyof InvoiceLine, value: any) => {
    const newLines = [...lines];
    newLines[index] = { ...newLines[index], [field]: value };
    setLines(newLines);
  };

  const calculateTotals = () => {
    let ht = 0;
    let vat = 0;
    lines.forEach(line => {
      const lineHt = line.quantity * line.unit_price_ht;
      ht += lineHt;
      vat += lineHt * (line.vat_rate / 100);
    });
    return { ht, vat, ttc: ht + vat };
  };

  const { ht, vat, ttc } = calculateTotals();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/invoices/', { 
        client_id: parseInt(clientId), 
        date_issued: dateIssued,
        lines 
      });
      setLines([{ description: '', quantity: 1, unit_price_ht: 0, vat_rate: 20 }]);
      setClientId('');
      fetchInvoices();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create invoice');
    }
  };

  const deleteInvoice = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this invoice?')) return;
    try {
      await api.delete(`/invoices/${id}`);
      fetchInvoices();
    } catch (err: any) {
      setError('Failed to delete invoice');
    }
  };

  const downloadPdf = (id: number) => {
    window.open(`/api/invoices/${id}/pdf`, '_blank');
  };

  return (
    <div style={{ padding: '20px' }}>
      <h2>Invoices</h2>
      
      <form onSubmit={handleSubmit} style={{ marginBottom: '40px', border: '1px solid #ccc', padding: '20px', borderRadius: '8px' }}>
        <h3>Create New Invoice</h3>
        <div style={{ marginBottom: '10px' }}>
          <label>Client: </label>
          <select value={clientId} onChange={e => setClientId(e.target.value)} required style={{ marginRight: '10px' }}>
            <option value="">Select a client</option>
            {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          
          <label> Date: </label>
          <input type="date" value={dateIssued} onChange={e => setDateIssued(e.target.value)} required />
        </div>

        <div style={{ margin: '20px 0' }}>
          <h4>Invoice Lines</h4>
          {lines.map((line, index) => (
            <div key={index} style={{ marginBottom: '10px', display: 'flex', gap: '10px', alignItems: 'center' }}>
              <input placeholder="Description" value={line.description} onChange={e => updateLine(index, 'description', e.target.value)} required />
              <input type="number" placeholder="Qty" value={line.quantity} onChange={e => updateLine(index, 'quantity', parseFloat(e.target.value))} required style={{ width: '60px' }} />
              <input type="number" placeholder="Price HT" value={line.unit_price_ht} onChange={e => updateLine(index, 'unit_price_ht', parseFloat(e.target.value))} required style={{ width: '100px' }} />
              <input type="number" placeholder="TVA %" value={line.vat_rate} onChange={e => updateLine(index, 'vat_rate', parseFloat(e.target.value))} required style={{ width: '60px' }} />
              <button type="button" onClick={() => removeLine(index)} style={{ color: 'red' }}>X</button>
            </div>
          ))}
          <button type="button" onClick={addLine}>+ Add Line</button>
        </div>

        <div style={{ textAlign: 'right', marginBottom: '20px' }}>
          <p>Total HT: <strong>{ht.toFixed(2)}€</strong></p>
          <p>Total TVA: <strong>{vat.toFixed(2)}€</strong></p>
          <p style={{ fontSize: '1.2em' }}>Total TTC: <strong>{ttc.toFixed(2)}€</strong></p>
        </div>

        <button type="submit" style={{ padding: '10px 20px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
          Create Invoice
        </button>
      </form>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      <h3>Existing Invoices</h3>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #ccc', textAlign: 'left' }}>
            <th>Number</th>
            <th>Client ID</th>
            <th>Date</th>
            <th>Total TTC</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {invoices.map(i => (
            <tr key={i.id} style={{ borderBottom: '1px solid #eee' }}>
              <td>{i.invoice_number}</td>
              <td>{i.client_id}</td>
              <td>{i.date_issued}</td>
              <td>{i.total_ttc.toFixed(2)}€</td>
              <td>
                <button onClick={() => downloadPdf(i.id)} style={{ marginRight: '5px' }}>PDF</button>
                <button onClick={() => deleteInvoice(i.id)} style={{ color: 'red' }}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default Invoices;
