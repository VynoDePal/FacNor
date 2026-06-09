import React, { useState, useEffect } from 'react';
import { Client } from '../types/client';
import { Invoice, InvoiceCreate, InvoiceLine } from '../types/invoice';
import { invoiceService } from '../api/invoiceApi';

interface InvoiceFormProps {
  clients: Client[];
  onSave: (invoice: Invoice) => void;
  onCancel: () => void;
}

const InvoiceForm: React.FC<InvoiceFormProps> = ({ clients, onSave, onCancel }) => {
  const [clientId, setClientId] = useState<number>('');
  const [issueDate, setIssueDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [dueDate, setDueDate] = useState<string>('');
  const [lines, setLines] = useState<InvoiceLine[]>([
    { description: '', quantity: 1, unit_price_ht: 0, tva_rate: 20, total_ht: 0 }
  ]);

  const [totals, setTotals] = useState({
    total_ht: 0,
    total_tva: 0,
    total_ttc: 0,
  });

  useEffect(() => {
    let totalHt = 0;
    let totalTva = 0;

    lines.forEach(line => {
      const lineTotalHt = line.quantity * line.unit_price_ht;
      totalHt += lineTotalHt;
      totalTva += lineTotalHt * (line.tva_rate / 100);
    });

    setTotals({
      total_ht: totalHt,
      total_tva: totalTva,
      total_ttc: totalHt + totalTva,
    });
  }, [lines]);

  const handleAddLine = () => {
    setLines([...lines, { description: '', quantity: 1, unit_price_ht: 0, tva_rate: 20, total_ht: 0 }]);
  };

  const handleRemoveLine = (index: number) => {
    if (lines.length > 1) {
      setLines(lines.filter((_, i) => i !== index));
    }
  };

  const handleLineChange = (index: number, field: keyof InvoiceLine, value: string | number) => {
    const newLines = [...lines];
    const line = { ...newLines[index], [field]: value };
    
    if (field === 'quantity' || field === 'unit_price_ht') {
      line.total_ht = line.quantity * line.unit_price_ht;
    }
    
    newLines[index] = line;
    setLines(newLines);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clientId) {
      alert('Veuillez sélectionner un client');
      return;
    }

    const invoiceData: InvoiceCreate = {
      client_id: clientId,
      issue_date: new Date(issueDate).toISOString(),
      due_date: dueDate ? new Date(dueDate).toISOString() : undefined,
      total_ht: totals.total_ht,
      total_tva: totals.total_tva,
      total_ttc: totals.total_ttc,
      status: 'draft',
      lines: lines.map(line => ({
        description: line.description,
        quantity: line.quantity,
        unit_price_ht: line.unit_price_ht,
        tva_rate: line.tva_rate,
        total_ht: line.total_ht,
      })),
    };

    try {
      const savedInvoice = await invoiceService.createInvoice(invoiceData);
      onSave(savedInvoice);
    } catch (err) {
      alert('Erreur lors de la création de la facture');
      console.error(err);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ maxWidth: '800px', margin: '0 auto', textAlign: 'left', padding: '1rem', border: '1px solid #ccc', borderRadius: '8px', backgroundColor: '#f9f9f9' }}>
      <h2>Création de Facture</h2>
      
      <div style={{ marginBottom: '1rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem' }}>Client :</label>
          <select 
            value={clientId || ''} 
            onChange={(e) => setClientId(parseInt(e.target.value))}
            style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}
          >
            <option value="">-- Sélectionner un client --</option>
            {clients.map(client => (
              <option key={client.id} value={client.id}>{client.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem' }}>Date d'émission :</label>
          <input 
            type="date" 
            value={issueDate} 
            onChange={(e) => setIssueDate(e.target.value)}
            style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}
          />
        </div>
      </div>

      <div style={{ marginBottom: '1rem' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem' }}>Date d'échéance :</label>
        <input 
          type="date" 
          value={dueDate} 
          onChange={(e) => setDueDate(e.target.value)}
          style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}
        />
      </div>

      <div style={{ marginBottom: '2rem' }}>
        <h3>Lignes de Facture</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '1rem' }}>
          <thead>
            <tr style={{ backgroundColor: '#eee', textAlign: 'left' }}>
              <th style={{ padding: '0.5rem', border: '1px solid #ccc' }}>Description</th>
              <th style={{ padding: '0.5rem', border: '1px solid #ccc', width: '80px' }}>Qté</th>
              <th style={{ padding: '0.5rem', border: '1px solid #ccc', width: '120px' }}>Prix HT</th>
              <th style={{ padding: '0.5rem', border: '1px solid #ccc', width: '80px' }}>TVA %</th>
              <th style={{ padding: '0.5rem', border: '1px solid #ccc', width: '120px' }}>Total HT</th>
              <th style={{ padding: '0.5rem', border: '1px solid #ccc', width: '50px' }}></th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line, index) => (
              <tr key={index}>
                <td style={{ padding: '0.5rem', border: '1px solid #ccc' }}>
                  <input 
                    type="text" 
                    value={line.description} 
                    onChange={(e) => handleLineChange(index, 'description', e.target.value)}
                    style={{ width: '100%', padding: '0.2rem', border: '1px solid #ccc', borderRadius: '4px' }}
                  />
                </td>
                <td style={{ padding: '0.5rem', border: '1px solid #ccc' }}>
                  <input 
                    type="number" 
                    value={line.quantity} 
                    onChange={(e) => handleLineChange(index, 'quantity', parseFloat(e.target.value) || 0)}
                    style={{ width: '100%', padding: '0.2rem', border: '1px solid #ccc', borderRadius: '4px' }}
                  />
                </td>
                <td style={{ padding: '0.5rem', border: '1px solid #ccc' }}>
                  <input 
                    type="number" 
                    step="0.01" 
                    value={line.unit_price_ht} 
                    onChange={(e) => handleLineChange(index, 'unit_price_ht', parseFloat(e.target.value) || 0)}
                    style={{ width: '100%', padding: '0.2rem', border: '1px solid #ccc', borderRadius: '4px' }}
                  />
                </td>
                <td style={{ padding: '0.5rem', border: '1px solid #ccc' }}>
                  <input 
                    type="number" 
                    value={line.tva_rate} 
                    onChange={(e) => handleLineChange(index, 'tva_rate', parseFloat(e.target.value) || 0)}
                    style={{ width: '100%', padding: '0.2rem', border: '1px solid #ccc', borderRadius: '4px' }}
                  />
                </td>
                <td style={{ padding: '0.5rem', border: '1px solid #ccc', textAlign: 'right' }}>
                  {(line.quantity * line.unit_price_ht).toFixed(2)} €
                </td>
                <td style={{ padding: '0.5rem', border: '1px solid #ccc', textAlign: 'center' }}>
                  <button 
                    type="button" 
                    onClick={() => handleRemoveLine(index)}
                    style={{ backgroundColor: '#dc3545', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                  >
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <button 
          type="button" 
          onClick={handleAddLine}
          style={{ padding: '0.5rem 1rem', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          + Ajouter une ligne
        </button>
      </div>

      <div style={{ textAlign: 'right', marginBottom: '2rem' }}>
        <div style={{ marginBottom: '0.5rem' }}>
          <strong>Total HT : {totals.total_ht.toFixed(2)} €</strong>
        </div>
        <div style={{ marginBottom: '0.5rem' }}>
          <strong>TVA Totale : {totals.total_tva.toFixed(2)} €</strong>
        </div>
        <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#000' }}>
          Total TTC : {totals.total_ttc.toFixed(2)} €
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
        <button 
          type="button" 
          onClick={onCancel}
          style={{ padding: '0.5rem 1rem', backgroundColor: '#6c757d', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          Annuler
        </button>
        <button 
          type="submit" 
          style={{ padding: '0.5rem 1rem', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          Enregistrer la Facture
        </button>
      </div>
    </form>
  );
};

export default InvoiceForm;
