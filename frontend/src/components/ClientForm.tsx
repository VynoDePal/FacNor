import React, { useState, useEffect } from 'react';
import { Client, ClientCreate } from '../types/client';

interface ClientFormProps {
  initialClient?: Client;
  onSave: (client: ClientCreate) => void;
  onCancel: () => void;
}

const ClientForm: React.FC<ClientFormProps> = ({ initialClient, onSave, onCancel }) => {
  const [formData, setFormData] = useState<ClientCreate>({
    name: initialClient?.name || '',
    email: initialClient?.email || '',
    address: initialClient?.address || '',
    vat_number: initialClient?.vat_number || '',
    siren: initialClient?.siren || '',
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div style={{ 
      marginTop: '2rem', 
      padding: '1rem', 
      border: '1px solid #ccc', 
      borderRadius: '8px', 
      maxWidth: '500px', 
      margin: '2rem auto',
      textAlign: 'left' 
    }}>
      <h3>{initialClient ? 'Modifier le Client' : 'Ajouter un Client'}</h3>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.25rem' }}>Nom *</label>
          <input 
            type="text" 
            name="name" 
            value={formData.name} 
            onChange={handleChange} 
            required 
            style={{ width: '100%', padding: '0.5rem' }}
          />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.25rem' }}>Email</label>
          <input 
            type="email" 
            name="email" 
            value={formData.email} 
            onChange={handleChange} 
            style={{ width: '100%', padding: '0.5rem' }}
          />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.25rem' }}>Adresse</label>
          <input 
            type="text" 
            name="address" 
            value={formData.address} 
            onChange={handleChange} 
            style={{ width: '100%', padding: '0.5rem' }}
          />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.25rem' }}>N° TVA intracommunautaire</label>
          <input 
            type="text" 
            name="vat_number" 
            value={formData.vat_number} 
            onChange={handleChange} 
            style={{ width: '100%', padding: '0.5rem' }}
          />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.25rem' }}>SIREN</label>
          <input 
            type="text" 
            name="siren" 
            value={formData.siren} 
            onChange={handleChange} 
            style={{ width: '100%', padding: '0.5rem' }}
          />
        </div>
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
          <button type="button" onClick={onCancel} style={{ padding: '0.5rem 1rem' }}>Annuler</button>
          <button type="submit" style={{ padding: '0.5rem 1rem', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Enregistrer</button>
        </div>
      </form>
    </div>
  );
};

export default ClientForm;
