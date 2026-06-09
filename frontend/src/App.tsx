import './App.css'
import React, { useState, useEffect } from 'react';
import ClientList from './components/ClientList';
import ClientForm from './components/ClientForm';
import InvoiceForm from './components/InvoiceForm';
import InvoiceList from './components/InvoiceList';
import { clientService } from './api/clientApi';
import { Client, ClientCreate } from './types/client';
import { Invoice } from './types/invoice';

function App() {
  const [clients, setClients] = useState<Client[]>([]);
  const [editingClient, setEditingClient] = useState<Client | null>(null);
  const [isAddingClient, setIsAddingClient] = useState(false);
  const [isAddingInvoice, setIsAddingInvoice] = useState(false);
  const [showInvoices, setShowInvoices] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadClients();
  }, []);

  const loadClients = async () => {
    try {
      const data = await clientService.getAllClients();
      setClients(data);
      setError(null);
    } catch (err) {
      setError('Erreur lors du chargement des clients');
      console.error(err);
    }
  };

  const handleSaveClient = async (clientData: ClientCreate) => {
    try {
      if (editingClient) {
        await clientService.updateClient(editingClient.id, clientData);
      } else {
        await clientService.createClient(clientData);
      }
      setEditingClient(null);
      setIsAddingClient(false);
      await loadClients();
    } catch (err) {
      setError('Erreur lors de l\'enregistrement du client');
      console.error(err);
    }
  };

  const handleDeleteClient = async (id: number) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer ce client ?')) {
      try {
        await clientService.deleteClient(id);
        await loadClients();
      } catch (err) {
        setError('Erreur lors de la suppression du client');
        console.error(err);
      }
  };

  const handleSaveInvoice = (invoice: Invoice) => {
    alert(`Facture ${invoice.invoice_number || ''} enregistrée avec succès !`);
    window.open(`/api/invoices/${invoice.id}/pdf`, '_blank');
    setIsAddingInvoice(false);
  };

  return (
    <div style={{ fontFamily: 'sans-serif', padding: '2rem', textAlign: 'center' }}>
      <h1>FacNor</h1>
      <p>Gestion de factures normalisées pour particuliers et entreprises</p>
      
      {error && (
        <div style={{ color: 'red', marginBottom: '1rem', fontWeight: 'bold' }}>
          {error}
        </div>
      )}

      <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'center', gap: '1rem' }}>
        {!isAddingClient && !editingClient && !isAddingInvoice && (
          <>
            <button 
              onClick={() => { setShowInvoices(false); setIsAddingClient(false); }} 
              style={{ padding: '0.5rem 1rem', backgroundColor: showInvoices ? '#6c757d' : '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '1rem' }}
            >
              Clients
            </button>
            <button 
              onClick={() => { setShowInvoices(true); setIsAddingClient(false); }} 
              style={{ padding: '0.5rem 1rem', backgroundColor: showInvoices ? '#007bff' : '#6c757d', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '1rem' }}
            >
              Factures
            </button>
            <button 
              onClick={() => setIsAddingClient(true)} 
              style={{ padding: '0.5rem 1rem', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '1rem' }}
            >
              + Ajouter un Client
            </button>
            <button 
              onClick={() => setIsAddingInvoice(true)} 
              style={{ padding: '0.5rem 1rem', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '1rem' }}
            >
              + Créer une Facture
            </button>
          </>
        )}
      </div>

        {(isAddingClient || editingClient) && (
          <ClientForm 
            initialClient={editingClient || undefined} 
            onSave={handleSaveClient} 
            onCancel={() => {
              setIsAddingClient(false);
              setEditingClient(null);
            }} 
          />
        )}

        {isAddingInvoice && (
          <InvoiceForm 
            clients={clients} 
            onSave={handleSaveInvoice} 
            onCancel={() => setIsAddingInvoice(false)} 
          />
        )}

        {!isAddingClient && !editingClient && (
          showInvoices ? (
            <InvoiceList clients={clients} />
          ) : (
            <ClientList clients={clients} onEdit={setEditingClient} onDelete={handleDeleteClient} />
          )
        )}
      </div>
    </div>
  );
}

export default App
