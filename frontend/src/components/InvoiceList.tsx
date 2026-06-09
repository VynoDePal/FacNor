import React, { useState, useEffect } from 'react';
import { Invoice } from '../types/invoice';
import { Client } from '../types/client';
import { invoiceService } from '../api/invoiceApi';

interface InvoiceListProps {
  clients: Client[];
}

const InvoiceList: React.FC<InvoiceListProps> = ({ clients }) => {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [filters, setFilters] = useState({
    client_id: '',
    start_date: '',
    end_date: '',
    min_amount: '',
    max_amount: '',
  });

  useEffect(() => {
    loadInvoices();
  }, []);

  const loadInvoices = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = {};
      if (filters.client_id) params.client_id = filters.client_id;
      if (filters.start_date) params.start_date = filters.start_date;
      if (filters.end_date) params.end_date = filters.end_date;
      if (filters.min_amount) params.min_amount = filters.min_amount;
      if (filters.max_amount) params.max_amount = filters.max_amount;

      const data = await invoiceService.getAllInvoices(params);
      setInvoices(data);
    } catch (err) {
      setError('Erreur lors du chargement des factures');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFilters(prev => ({ ...prev, [name]: value }));
  };

  const handleApplyFilters = () => {
    loadInvoices();
  };

  const handleClearFilters = () => {
    setFilters({
      client_id: '',
      start_date: '',
      end_date: '',
      min_amount: '',
      max_amount: '',
    });
  };

  // Use a timeout or useEffect to clear filters and reload if we want auto-update
  // For now, we use an explicit "Apply" button for better UX when dealing with dates/amounts.

  return (
    <div style={{ marginTop: '2rem', textAlign: 'left', maxWidth: '1000px', margin: '2rem auto', padding: '1rem', border: '1px solid #ddd', borderRadius: '8px', backgroundColor: '#f9f9f9' }}>
      <h2>Liste des Factures</h2>
      
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem', padding: '1rem', backgroundColor: '#fff', border: '1px solid #eee', borderRadius: '4px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
          <label style={{ fontSize: '0.9rem', fontWeight: 'bold' }}>Client</label>
          <select 
            name="client_id" 
            value={filters.client_id} 
            onChange={handleFilterChange}
            style={{ padding: '0.4rem', borderRadius: '4px', border: '1px solid #ccc' }}
          >
            <option value="">Tous les clients</option>
            {clients.map(client => (
              <option key={client.id} value={client.id}>{client.name}</option>
            ))}
          </select>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
          <label style={{ fontSize: '0.9rem', fontWeight: 'bold' }}>Date début</label>
          <input 
            type="date" 
            name="start_date" 
            value={filters.start_date} 
            onChange={handleFilterChange}
            style={{ padding: '0.4rem', borderRadius: '4px', border: '1px solid #ccc' }}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
          <label style={{ fontSize: '0.9rem', fontWeight: 'bold' }}>Date fin</label>
          <input 
            type="date" 
            name="end_date" 
            value={filters.end_date} 
            onChange={handleFilterChange}
            style={{ padding: '0.4rem', borderRadius: '4px', border: '1px solid #ccc' }}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
          <label style={{ fontSize: '0.9rem', fontWeight: 'bold' }}>Montant Min (TTC)</label>
          <input 
            type="number" 
            name="min_amount" 
            value={filters.min_amount} 
            onChange={handleFilterChange}
            style={{ padding: '0.4rem', borderRadius: '4px', border: '1px solid #ccc' }}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
          <label style={{ fontSize: '0.9rem', fontWeight: 'bold' }}>Montant Max (TTC)</label>
          <input 
            type="number" 
            name="max_amount" 
            value={filters.max_amount} 
            onChange={handleFilterChange}
            style={{ padding: '0.4rem', borderRadius: '4px', border: '1px solid #ccc' }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.5rem' }}>
          <button 
            onClick={handleApplyFilters}
            style={{ padding: '0.5rem 1rem', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            Filtrer
          </button>
          <button 
            onClick={handleClearFilters}
            style={{ padding: '0.5rem 1rem', backgroundColor: '#6c757d', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            Réinitialiser
          </button>
        </div>
      </div>

      {error && <div style={{ color: 'red', marginBottom: '1rem' }}>{error}</div>}
      
      {loading ? (
        <div>Chargement...</div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem' }}>
          <thead>
            <tr style={{ backgroundColor: '#eee', textAlign: 'left' }}>
              <th style={{ padding: '0.8rem', borderBottom: '2px solid #ddd' }}>N° Facture</th>
              <th style={{ padding: '0.8rem', borderBottom: '2px solid #ddd' }}>Client</th>
              <th style={{ padding: '0.8rem', borderBottom: '2px solid #ddd' }}>Date</th>
              <th style={{ padding: '0.8rem', borderBottom: '2px solid #ddd' }}>Montant TTC</th>
              <th style={{ padding: '0.8rem', borderBottom: '2px solid #ddd' }}>Statut</th>
              <th style={{ padding: '0.8rem', borderBottom: '2px solid #ddd' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {invoices.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: '1rem', textAlign: 'center' }}>Aucune facture trouvée</td>
              </tr>
            ) : (
              invoices.map(invoice => {
                const client = clients.find(c => c.id === invoice.client_id);
                return (
                  <tr key={invoice.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '0.8rem' }}>{invoice.invoice_number}</td>
                    <td style={{ padding: '0.8rem' }}>{client ? client.name : 'Inconnu'}</td>
                    <td style={{ padding: '0.8rem' }}>{invoice.issue_date ? new Date(invoice.issue_date).toLocaleDateString() : 'N/A'}</td>
                    <td style={{ padding: '0.8rem' }}>{invoice.total_ttc} €</td>
                    <td style={{ padding: '0.8rem' }}>
                      <span style={{ 
                        padding: '0.2rem 0.5rem', 
                        borderRadius: '4px', 
                        fontSize: '0.8rem', 
                        backgroundColor: invoice.status === 'paid' ? '#d4edda' : (invoice.status === 'draft' ? '#fff3cd' : '#f8d7da'),
                        color: invoice.status === 'paid' ? '#155724' : (invoice.status === 'draft' ? '#856404' : '#721c24')
                      }}>
                        {invoice.status}
                      </span>
                    </td>
                    <td style={{ padding: '0.8rem' }}>
                      <button 
                        onClick={() => window.open(`/api/invoices/${invoice.id}/pdf`, '_blank')}
                        style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem', backgroundColor: '#17a2b8', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                      >
                        PDF
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default InvoiceList;
