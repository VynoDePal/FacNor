import React, { useState, useEffect } from 'react';
import { invoiceService, clientService } from '../services/api';

interface Invoice {
  id: number;
  invoice_number: string;
  date: string;
  due_date: string;
  client_id: number;
  total_ttc: number;
  status: string;
}

interface Client {
  id: number;
  name: string;
}

const InvoiceList: React.FC = () => {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [filterClientId, setFilterClientId] = useState<string>('');
  const [filterStartDate, setFilterStartDate] = useState<string>('');
  const [filterEndDate, setFilterEndDate] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchClients = async () => {
      try {
        const data = await clientService.getAll();
        setClients(data);
      } catch (err) {
        console.error("Failed to fetch clients", err);
      }
    };
    fetchClients();
  }, []);

  useEffect(() => {
    const fetchInvoices = async () => {
      setLoading(true);
      try {
        const params = {
          client_id: filterClientId || undefined,
          start_date: filterStartDate || undefined,
          end_date: filterEndDate || undefined,
        };
        const data = await invoiceService.getAll(params);
        setInvoices(data);
        setError(null);
      } catch (err: any) {
        setError(err.response?.data?.detail || "Une erreur est survenue lors du chargement des factures.");
      } finally {
        setLoading(false);
      }
    };
    fetchInvoices();
  }, [filterClientId, filterStartDate, filterEndDate]);

  return (
    <div style={{ marginTop: '20px', borderTop: '1px solid #ccc', paddingTop: '20px' }}>
      <h2>Liste des Factures</h2>
      
      <div style={{ marginBottom: '20px', display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '5px' }}>Client:</label>
          <select 
            value={filterClientId} 
            onChange={(e) => setFilterClientId(e.target.value)}
            style={{ padding: '5px' }}
          >
            <option value="">Tous les clients</option>
            {clients.map(client => (
              <option key={client.id} value={client.id}>{client.name}</option>
            ))}
          </select>
        </div>
        
        <div>
          <label style={{ display: 'block', marginBottom: '5px' }}>Date début:</label>
          <input 
            type="date" 
            value={filterStartDate} 
            onChange={(e) => setFilterStartDate(e.target.value)}
            style={{ padding: '5px' }}
          />
        </div>
        
        <div>
          <label style={{ display: 'block', marginBottom: '5px' }}>Date fin:</label>
          <input 
            type="date" 
            value={filterEndDate} 
            onChange={(e) => setFilterEndDate(e.target.value)}
            style={{ padding: '5px' }}
          />
        </div>
      </div>

      {error && <div style={{ color: 'red', marginBottom: '10px' }}>{error}</div>}
      
      {loading ? (
        <p>Chargement...</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ backgroundColor: '#f2f2f2', borderBottom: '2px solid #ddd' }}>
              <th style={{ padding: '10px', border: '1px solid #ddd' }}>N° Facture</th>
              <th style={{ padding: '10px', border: '1px solid #ddd' }}>Client</th>
              <th style={{ padding: '10px', border: '1px solid #ddd' }}>Date</th>
              <th style={{ padding: '10px', border: '1px solid #ddd' }}>Total TTC</th>
              <th style={{ padding: '10px', border: '1px solid #ddd' }}>Statut</th>
            </tr>
          </thead>
          <tbody>
            {invoices.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: '10px', textAlign: 'center', border: '1px solid #ddd' }}>
                  Aucune facture trouvée.
                </td>
              </tr>
            ) : (
              invoices.map(invoice => (
                <tr key={invoice.id} style={{ borderBottom: '1px solid #ddd' }}>
                  <td style={{ padding: '10px', border: '1px solid #ddd' }}>{invoice.invoice_number}</td>
                  <td style={{ padding: '10px', border: '1px solid #ddd' }}>
                    {clients.find(c => c.id === invoice.client_id)?.name || 'Inconnu'}
                  </td>
                  <td style={{ padding: '10px', border: '1px solid #ddd' }}>
                    {new Date(invoice.date).toLocaleDateString()}
                  </td>
                  <td style={{ padding: '10px', border: '1px solid #ddd' }}>
                    {invoice.total_ttc} €
                  </td>
                  <td style={{ padding: '10px', border: '1px solid #ddd' }}>
                    {invoice.status}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default InvoiceList;
