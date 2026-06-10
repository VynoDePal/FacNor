import React, { useState, useEffect } from 'react';
import { invoiceService, clientService } from '../services/api';

interface Client {
  id: number;
  name: string;
}

interface Invoice {
  id: number;
  invoice_number: string;
  date: string;
  total_ttc: number;
  client_id: number;
  status: string;
}

const InvoiceList: React.FC = () => {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [filterClientId, setFilterClientId] = useState<string>('');
  const [filterDate, setFilterDate] = useState<string>('');

  useEffect(() => {
    fetchClients();
    fetchInvoices();
  }, []);

  useEffect(() => {
    fetchInvoices();
  }, [filterClientId, filterDate]);

  const fetchClients = async () => {
    try {
      const data = await clientService.getAll();
      setClients(data);
    } catch (err) {
      console.error('Error fetching clients:', err);
    }
  };

  const fetchInvoices = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (filterClientId) params.client_id = filterClientId;
      if (filterDate) params.date = filterDate;
      
      const data = await invoiceService.getAll(params);
      setInvoices(data);
    } catch (err) {
      setError('Failed to fetch invoices');
      console.error('Error fetching invoices:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="invoice-list-container">
      <h2>Liste des Factures</h2>
      
      <div className="filters" style={{ marginBottom: '20px', display: 'flex', gap: '10px' }}>
        <div>
          <label>Client: </label>
          <select 
            value={filterClientId} 
            onChange={(e) => setFilterClientId(e.target.value)}
          >
            <option value="">Tous les clients</option>
            {clients.map(client => (
              <option key={client.id} value={client.id}>{client.name}</option>
            ))}
          </select>
        </div>
        
        <div>
          <label>Date: </label>
          <input 
            type="date" 
            value={filterDate} 
            onChange={(e) => setFilterDate(e.target.value)}
          />
        </div>
        
        <button onClick={() => { setFilterClientId(''); setFilterDate(''); }}>
          Réinitialiser
        </button>
      </div>

      {error && <div className="error-message" style={{ color: 'red' }}>{error}</div>}
      
      {loading ? (
        <p>Chargement...</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #ccc' }}>
              <th>N° Facture</th>
              <th>Date</th>
              <th>Client ID</th>
              <th>Total TTC</th>
              <th>Statut</th>
            </tr>
          </thead>
          <tbody>
            {invoices.length > 0 ? (
              invoices.map(invoice => (
                <tr key={invoice.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td>{invoice.invoice_number}</td>
                  <td>{new Date(invoice.date).toLocaleDateString()}</td>
                  <td>{invoice.client_id}</td>
                  <td>{invoice.total_ttc} €</td>
                  <td>{invoice.status}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center' }}>Aucune facture trouvée</td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default InvoiceList;
