import React from 'react';
import { Client } from '../types/client';

interface ClientListProps {
  clients: Client[];
  onEdit: (client: Client) => void;
  onDelete: (id: number) => void;
}

const ClientList: React.FC<ClientListProps> = ({ clients, onEdit, onDelete }) => {
  return (
    <div style={{ marginTop: '2rem' }}>
      <h2>Liste des Clients</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #ccc', textAlign: 'left' }}>
            <th>Nom</th>
            <th>Email</th>
            <th>SIREN</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {clients.map((client) => (
            <tr key={client.id} style={{ borderBottom: '1px solid #eee' }}>
              <td>{client.name}</td>
              <td>{client.email}</td>
              <td>{client.siren}</td>
              <td>
                <button onClick={() => onEdit(client)} style={{ marginRight: '0.5rem' }}>Modifier</button>
                <button onClick={() => onDelete(client.id)} style={{ color: 'red' }}>Supprimer</button>
              </td>
            </tr>
          ))}
          {clients.length === 0 && (
            <tr>
              <td colSpan={4} style={{ textAlign: 'center', padding: '1rem' }}>Aucun client trouvé.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

export default ClientList;
