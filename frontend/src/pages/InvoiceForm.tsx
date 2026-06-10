import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { factureService } from '../services/factureService';
import { clientService } from '../services/clientService';
import { Facture, FactureCreate, LigneFacture } from '../types/facture';

const InvoiceForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [clients, setClients] = useState<any[]>([]);
  const [formData, setFormData] = useState<FactureCreate>({
    client_id: 0,
    date_facture: new Date().toISOString().split('T')[0],
    date_echeance: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    statut: 'Brouillon',
    notes: '',
    lignes: [],
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchClients();
    if (id) {
      fetchInvoice();
    }
  }, [id]);

  const fetchClients = async () => {
    try {
      const response = await clientService.getAllClients();
      setClients(response.data);
    } catch (err) {
      console.error('Failed to fetch clients', err);
      setError('Error loading clients');
    }
  };

  const fetchInvoice = async () => {
    try {
      setLoading(true);
      const response = await factureService.getFactureById(id!);
      const facture = response.data;
      setFormData({
        client_id: facture.client_id,
        date_facture: facture.date_facture,
        date_echeance: facture.date_echeance,
        statut: facture.statut,
        notes: facture.notes || '',
        lignes: facture.lignes,
      });
    } catch (err) {
      console.error('Failed to fetch invoice', err);
      setError('Error loading invoice');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    
    if (name === 'client_id') {
      setFormData(prev => ({ ...prev, [name]: parseInt(value, 10) || 0 }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
  };

  const addLine = () => {
    const newLine: LigneFacture = {
      description: '',
      quantite: 1,
      prix_unitaire: 0,
      montant_ht: 0,
      tva_taux: 20,
      montant_tva: 0,
      montant_ttc: 0,
    };
    setFormData(prev => ({ ...prev, lignes: [...prev.lignes, newLine] }));
  };

  const removeLine = (index: number) => {
    setFormData(prev => ({
      ...prev,
      lignes: prev.lignes.filter((_, i) => i !== index),
    }));
  };

  const updateLine = (index: number, updates: Partial<LigneFacture>) => {
    const updatedLignes = [...formData.lignes];
    const line = { ...updatedLignes[index], ...updates };
    
    // Calculations
    line.montant_ht = line.quantite * line.prix_unitaire;
    line.montant_tva = line.montant_ht * (line.tva_taux / 100);
    line.montant_ttc = line.montant_ht + line.montant_tva;
    
    updatedLignes[index] = line;
    setFormData(prev => ({ ...prev, lignes: updatedLignes }));
  };

  const calculateTotals = () => {
    const totalHT = formData.lignes.reduce((sum, line) => sum + line.montant_ht, 0);
    const totalTVA = formData.lignes.reduce((sum, line) => sum + line.montant_tva, 0);
    const totalTTC = formData.lignes.reduce((sum, line) => sum + line.montant_ttc, 0);
    return { totalHT, totalTVA, totalTTC };
  };

  const { totalHT, totalTVA, totalTTC } = calculateTotals();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      if (id) {
        await factureService.updateFacture(id, formData);
      } else {
        await factureService.createFacture(formData);
      }
      navigate('/factures');
    } catch (err) {
      console.error('Failed to save invoice', err);
      setError('Failed to save invoice. Please check your inputs.');
    }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div style={{ color: 'red' }}>{error}</div>;

  return (
    <div>
      <h1>{id ? 'Edit Invoice' : 'Create Invoice'}</h1>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          <div>
            <label>Client: </label>
            <select 
              name="client_id" 
              value={formData.client_id} 
              onChange={handleInputChange} 
              required 
              style={{ width: '100%', padding: '8px' }}
            >
              <option value="">Select a client</option>
              {clients.map(client => (
                <option key={client.id} value={client.id}>{client.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label>Status: </label>
            <select 
              name="statut" 
              value={formData.statut} 
              onChange={handleInputChange} 
              style={{ width: '100%', padding: '8px' }}
            >
              <option value="Brouillon">Brouillon</option>
              <option value="Envoyée">Envoyée</option>
              <option value="Payée">Payée</option>
              <option value="Annulée">Annulée</option>
            </select>
          </div>
          <div>
            <label>Invoice Date: </label>
            <input 
              type="date" 
              name="date_facture" 
              value={formData.date_facture} 
              onChange={handleInputChange} 
              required 
              style={{ width: '100%', padding: '8px' }}
            />
          </div>
          <div>
            <label>Due Date: </label>
            <input 
              type="date" 
              name="date_echeance" 
              value={formData.date_echeance} 
              onChange={handleInputChange} 
              required 
              style={{ width: '100%', padding: '8px' }}
            />
          </div>
        </div>

        <div>
          <label>Notes: </label>
          <textarea 
            name="notes" 
            value={formData.notes} 
            onChange={handleInputChange} 
            style={{ width: '100%', padding: '8px', height: '60px' }}
          />
        </div>

        <div>
          <h3>Invoice Lines</h3>
          <table border="1" style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th>Description</th>
                <th>Qty</th>
                <th>Unit Price</th>
                <th>TVA %</th>
                <th>HT</th>
                <th>TVA</th>
                <th>TTC</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {formData.lignes.map((line, index) => (
                <tr key={index}>
                  <td>
                    <input 
                      type="text" 
                      value={line.description} 
                      onChange={(e) => updateLine(index, { description: e.target.value })}
                      style={{ width: '100%' }}
                    />
                  </td>
                  <td>
                    <input 
                      type="number" 
                      value={line.quantite} 
                      onChange={(e) => updateLine(index, { quantite: parseFloat(e.target.value) || 0 })}
                      style={{ width: '50px' }}
                    />
                  </td>
                  <td>
                    <input 
                      type="number" 
                      step="0.01" 
                      value={line.prix_unitaire} 
                      onChange={(e) => updateLine(index, { prix_unitaire: parseFloat(e.target.value) || 0 })}
                      style={{ width: '80px' }}
                    />
                  </td>
                  <td>
                    <input 
                      type="number" 
                      value={line.tva_taux} 
                      onChange={(e) => updateLine(index, { tva_taux: parseFloat(e.target.value) || 0 })}
                      style={{ width: '50px' }}
                    />
                  </td>
                  <td>{line.montant_ht.toFixed(2)}</td>
                  <td>{line.montant_tva.toFixed(2)}</td>
                  <td>{line.montant_ttc.toFixed(2)}</td>
                  <td>
                    <button type="button" onClick={() => removeLine(index)}>Remove</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <button type="button" onClick={addLine} style={{ marginTop: '10px' }}>Add Line</button>
        </div>

        <div style={{ textAlign: 'right', fontSize: '1.2em' }}>
          <p>Total HT: {totalHT.toFixed(2)} €</p>
          <p>Total TVA: {totalTVA.toFixed(2)} €</p>
          <p><strong>Total TTC: {totalTTC.toFixed(2)} €</strong></p>
        </div>

        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
          <button type="button" onClick={() => navigate('/factures')}>Cancel</button>
          <button type="submit" style={{ background: '#007bff', color: 'white', padding: '10px 20px', border: 'none', cursor: 'pointer' }}>Save Invoice</button>
        </div>
      </form>
    </div>
  );
};

export default InvoiceForm;
