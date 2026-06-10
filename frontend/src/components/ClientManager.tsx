import React, { useEffect, useState } from 'react';
import { clientService } from '../services/api';

interface Client {
  id: number;
  name: string;
  email?: string;
  address?: string;
  vat_number?: string;
  is_business: boolean;
}

const ClientManager: React.FC = () => {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState<Partial<Client>>({
    name: '',
    email: '',
    address: '',
    vat_number: '',
    is_business: false,
  });

  // Edit state
  const [editingId, setEditingId] = useState<number | null>(null);

  useEffect(() => {
    fetchClients();
  }, []);

  const fetchClients = async () => {
    try {
      setLoading(true);
      const data = await clientService.getAll();
      setClients(data);
      setError(null);
    } catch (err) {
      console.error('Error fetching clients:', err);
      setError('Failed to fetch clients.');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    const val = type === 'checkbox' ? (e.target as HTMLInputElement).checked : value;
    setFormData((prev) => ({ ...prev, [name]: val }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await clientService.update(editingId, formData);
      } else {
        await clientService.create(formData);
      }
      setFormData({
        name: '',
        email: '',
        address: '',
        vat_number: '',
        is_business: false,
      });
      setEditingId(null);
      fetchClients();
    } catch (err) {
      console.error('Error saving client:', err);
      alert('Failed to save client.');
    }
  };

  const handleEdit = (client: Client) => {
    setEditingId(client.id);
    setFormData({
      name: client.name,
      email: client.email || '',
      address: client.address || '',
      vat_number: client.vat_number || '',
      is_business: client.is_business,
    });
  };

  const handleDelete = async (id: number) => {
    if (window.confirm('Are you sure you want to delete this client?')) {
      try {
        await clientService.delete(id);
        fetchClients();
      } catch (err) {
        console.error('Error deleting client:', err);
        alert('Failed to delete client.');
      }
    }
  };

  const handleCancel = () => {
    setEditingId(null);
    setFormData({
      name: '',
      email: '',
      address: '',
      vat_number: '',
      is_business: false,
    });
  };

  if (loading) return <div>Loading clients...</div>;
  if (error) return <div style={{ color: 'red' }}>{error}</div>;

  return (
    <div style={{ padding: '20px' }}>
      <h2>Gestion des Clients</h2>

      {/* Form */}
      <section style={{ marginBottom: '30px', border: '1px solid #ccc', padding: '15px' }}>
        <h3>{editingId ? 'Modifier le client' : 'Nouveau client'}</h3>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '10px' }}>
            <label>Nom: </label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              required
            />
          </div>
          <div style={{ marginBottom: '10px' }}>
            <label>Email: </label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleInputChange}
            />
          </div>
          <div style={{ marginBottom: '10px' }}>
            <label>Adresse: </label>
            <textarea
              name="address"
              value={formData.address}
              onChange={handleInputChange}
            />
          </div>
          <div style={{ marginBottom: '10px' }}>
            <label>Numéro de TVA: </label>
            <input
              type="text"
              name="vat_number"
              value={formData.vat_number}
              onChange={handleInputChange}
            />
          </div>
          <div style={{ marginBottom: '10px' }}>
            <label>
              <input
              type="checkbox"
              name="is_business"
              checked={formData.is_business}
              onChange={handleInputChange}
            />
            Client professionnel (B2B)
          </label>
          </div>
          <button type="submit">{editingId ? 'Mettre à jour' : 'Créer'}</button>
          {editingId && <button type="button" onClick={handleCancel} style={{ marginLeft: '10px' }}>Annuler</button>}
        </form>
      </section>

      {/* List */}
      <section>
        <h3>Liste des clients</h3>
        <table border={1} cellPadding={10} style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th>Nom</th>
              <th>Email</th>
              <th>Type</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {clients.map((client) => (
              <tr key={client.id}>
                <td>{client.name}</td>
                <td>{client.email || '-'}</td>
                <td>{client.is_business ? 'B2B' : 'B2C'}</td>
                <td>
                  <button onClick={() => handleEdit(client)}>Modifier</button>
                  <button onClick={() => handleDelete(client.id)} style={{ color: 'red' }}>Supprimer</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
};

export default ClientManager;
