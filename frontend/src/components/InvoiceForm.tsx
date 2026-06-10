import React, { useState, useEffect } from 'react';
import { clientService, invoiceService } from '../services/api';

interface InvoiceLine {
  description: string;
  quantity: number;
  unit_price: number;
  tax_rate: number;
  total_ht: number;
  total_tva: number;
  total_ttc: number;
}

interface InvoiceFormState {
  date: string;
  due_date: string;
  client_id: number;
  user_id: number;
  status: string;
  lines: InvoiceLine[];
}

const InvoiceForm: React.FC = () => {
  const [clients, setClients] = useState<any[]>([]);
  const [formData, setFormData] = useState<InvoiceFormState>({
    date: new Date().toISOString().split('T')[0],
    due_date: '',
    client_id: 0,
    user_id: 1, // Default user for demo purposes, in real app would come from auth
    status: 'draft',
    lines: [{ description: '', quantity: 1, unit_price: 0, tax_rate: 20, total_ht: 0, total_tva: 0, total_ttc: 0 }],
  });

  const [totals, setTotals] = useState({ ht: 0, tva: 0, ttc: 0 });

  useEffect(() => {
    const fetchClients = async () => {
      try {
        const data = await clientService.getAll();
        setClients(data);
      } catch (error) {
        console.error('Error fetching clients:', error);
      }
    };
    fetchClients();
  }, []);

  useEffect(() => {
    // Calculate totals whenever lines change
    let totalHt = 0;
    let totalTva = 0;
    let totalTtc = 0;

    formData.lines.forEach(line => {
      const ht = line.quantity * line.unit_price;
      const tva = ht * (line.tax_rate / 100);
      const ttc = ht + tva;
      totalHt += ht;
      totalTva += tva;
      totalTtc += ttc;
    });

    setTotals({ ht: totalHt, tva: totalTva, ttc: totalTtc });
  }, [formData.lines]);

  const handleLineChange = (index: number, field: keyof InvoiceLine, value: any) => {
    const newLines = [...formData.lines];
    newLines[index] = { ...newLines[index], [field]: value };
    
    // Recalculate line totals
    const line = newLines[index];
    line.total_ht = line.quantity * line.unit_price;
    line.total_tva = line.total_ht * (line.tax_rate / 100);
    line.total_ttc = line.total_ht + line.total_tva;

    setFormData({ ...formData, lines: newLines });
  };

  const addLine = () => {
    setFormData({
      ...formData,
      lines: [...formData.lines, { description: '', quantity: 1, unit_price: 0, tax_rate: 20, total_ht: 0, total_tva: 0, total_ttc: 0 }],
    });
  };

  const removeLine = (index: number) => {
    if (formData.lines.length > 1) {
      const newLines = formData.lines.filter((_, i) => i !== index);
      setFormData({ ...formData, lines: newLines });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        total_ht: totals.ht,
        total_tva: totals.tva,
        total_ttc: totals.ttc,
      };
      await invoiceService.create(payload);
      alert('Invoice created successfully!');
      // Reset form or redirect
    } catch (error) {
      console.error('Error creating invoice:', error);
      alert('Error creating invoice');
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h2>Create New Invoice</h2>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '20px', display: 'flex', gap: '10px' }}>
          <div>
            <label>Date: </label>
            <input 
              type="date" 
              value={formData.date} 
              onChange={(e) => setFormData({ ...formData, date: e.target.value })} 
            />
          </div>
          <div>
            <label>Due Date: </label>
            <input 
              type="date" 
              value={formData.due_date} 
              onChange={(e) => setFormData({ ...formData, due_date: e.target.value })} 
            />
          </div>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label>Client: </label>
          <select 
            value={formData.client_id} 
            onChange={(e) => setFormData({ ...formData, client_id: parseInt(e.target.value) })}
            required
          >
            <option value="">Select a client</option>
            {clients.map(client => (
              <option key={client.id} value={client.id}>{client.name}</option>
            ))}
          </select>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <h3>Items</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '1px solid #ccc' }}>
                <th>Description</th>
                <th>Qty</th>
                <th>Unit Price</th>
                <th>Tax %</th>
                <th>Total TTC</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {formData.lines.map((line, index) => (
                <tr key={index}>
                  <td>
                    <input 
                      type="text" 
                      value={line.description} 
                      onChange={(e) => handleLineChange(index, 'description', e.target.value)} 
                      required 
                    />
                  </td>
                  <td>
                    <input 
                      type="number" 
                      value={line.quantity} 
                      onChange={(e) => handleLineChange(index, 'quantity', parseFloat(e.target.value) || 0)} 
                      style={{ width: '50px' }}
                      required 
                    />
                  </td>
                  <td>
                    <input 
                      type="number" 
                      value={line.unit_price} 
                      onChange={(e) => handleLineChange(index, 'unit_price', parseFloat(e.target.value) || 0)} 
                      style={{ width: '80px' }}
                      required 
                    />
                  </td>
                  <td>
                    <input 
                      type="number" 
                      value={line.tax_rate} 
                      onChange={(e) => handleLineChange(index, 'tax_rate', parseFloat(e.target.value) || 0)} 
                      style={{ width: '50px' }}
                      required 
                    />
                  </td>
                  <td>{line.total_ttc.toFixed(2)} €</td>
                  <td>
                    <button type="button" onClick={() => removeLine(index)}>Remove</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <button type="button" onClick={addLine} style={{ marginTop: '10px' }}>Add Line</button>
        </div>

        <div style={{ textAlign: 'right', marginBottom: '20px' }}>
          <p>Total HT: {totals.ht.toFixed(2)} €</p>
          <p>Total TVA: {totals.tva.toFixed(2)} €</p>
          <p><strong>Total TTC: {totals.ttc.toFixed(2)} €</strong></p>
        </div>

        <button type="submit" style={{ padding: '10px 20px', fontSize: '16px', cursor: 'pointer' }}>Create Invoice</button>
      </form>
    </div>
  );
};

export default InvoiceForm;
