import React, { useState, useEffect } from 'react';
import { clientService } from '../services/clientService';

const ClientForm = ({ clientId = null }) => {
  const [client, setClient] = useState({
    name: '',
    email: '',
    phone: '',
    type: 'B2C',
    entreprise: '',
    siret: '',
    vat_number: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (clientId) {
      fetchClient();
    }
  }, [clientId]);

  const fetchClient = async () => {
    try {
      const response = await clientService.getClientById(clientId);
      setClient(response.data);
    } catch (err) {
      setError('Failed to fetch client details');
      console.error(err);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setClient(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (clientId) {
        await clientService.updateClient(clientId, client);
      } else {
        await clientService.createClient(client);
      }
      window.location.href = '/clients';
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred while saving the client');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>{clientId ? 'Edit Client' : 'Create Client'}</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label>Name:</label>
          <input name="name" value={client.name} onChange={handleChange} required />
        </div>
        <div>
          <label>Email:</label>
          <input name="email" type="email" value={client.email} onChange={handleChange} required />
        </div>
        <div>
          <label>Phone:</label>
          <input name="phone" value={client.phone} onChange={handleChange} />
        </div>
        <div>
          <label>Type:</label>
          <select name="type" value={client.type} onChange={handleChange}>
            <option value="B2B">B2B</option>
            <option value="B2C">B2C</option>
          </select>
        </div>
        {client.type === 'B2B' && (
          <>
            <div>
              <label>Entreprise Name:</label>
              <input name="entreprise" value={client.entreprise} onChange={handleChange} required={client.type === 'B2B'} />
            </div>
            <div>
              <label>SIRET:</label>
              <input name="siret" value={client.siret} onChange={handleChange} />
            </div>
            <div>
              <label>VAT Number:</label>
              <input name="vat_number" value={client.vat_number} onChange={handleChange} />
            </div>
          </>
        )}
        <div style={{ marginTop: '10px' }}>
          <button type="submit" disabled={loading}>
            {loading ? 'Saving...' : clientId ? 'Update Client' : 'Create Client'}
          </button>
          <button type="button" onClick={() => window.location.href = '/clients'} style={{ marginLeft: '10px' }}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default ClientForm;
