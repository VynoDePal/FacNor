import { FormEvent, useEffect, useMemo, useState } from 'react';
import {
  AuthUser,
  Client,
  ClientPayload,
  createClient,
  fetchClients,
  fetchCurrentUser,
  login,
  updateClient,
} from './api';
import './styles.css';

const TOKEN_STORAGE_KEY = 'facnor_access_token';
const EMPTY_CLIENT_FORM: ClientPayload = {
  name: '',
  email: '',
  address: '',
  postal_code: '',
  city: '',
  country: 'France',
  siren: '',
  vat_number: '',
};

type ClientFormField = keyof ClientPayload;

function normalizeClientPayload(form: ClientPayload): ClientPayload {
  return {
    name: form.name.trim(),
    email: form.email?.trim() || null,
    address: form.address.trim(),
    postal_code: form.postal_code.trim(),
    city: form.city.trim(),
    country: form.country.trim() || 'France',
    siren: form.siren?.trim() || null,
    vat_number: form.vat_number?.trim() || null,
  };
}

function formFromClient(client: Client): ClientPayload {
  return {
    name: client.name,
    email: client.email ?? '',
    address: client.address,
    postal_code: client.postal_code,
    city: client.city,
    country: client.country,
    siren: client.siren ?? '',
    vat_number: client.vat_number ?? '',
  };
}

function App() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY));
  const [user, setUser] = useState<AuthUser | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<number | null>(null);
  const [clientForm, setClientForm] = useState<ClientPayload>(EMPTY_CLIENT_FORM);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSavingClient, setIsSavingClient] = useState(false);

  const selectedClient = useMemo(
    () => clients.find((client) => client.id === selectedClientId) ?? null,
    [clients, selectedClientId],
  );

  useEffect(() => {
    if (!token) {
      setUser(null);
      setClients([]);
      return;
    }

    fetchCurrentUser(token)
      .then(setUser)
      .catch(() => {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        setToken(null);
      });
  }, [token]);

  useEffect(() => {
    if (!token || !user) {
      return;
    }

    fetchClients(token)
      .then(setClients)
      .catch((caught) => setError(caught instanceof Error ? caught.message : 'Chargement des clients impossible'));
  }, [token, user]);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setSuccess('');
    setIsLoading(true);

    try {
      const auth = await login(email, password);
      localStorage.setItem(TOKEN_STORAGE_KEY, auth.access_token);
      setToken(auth.access_token);
      setUser(auth.user);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Connexion impossible');
    } finally {
      setIsLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
    setClients([]);
    setSelectedClientId(null);
    setClientForm(EMPTY_CLIENT_FORM);
    setPassword('');
  }

  function startNewClient() {
    setSelectedClientId(null);
    setClientForm(EMPTY_CLIENT_FORM);
    setError('');
    setSuccess('');
  }

  function selectClient(client: Client) {
    setSelectedClientId(client.id);
    setClientForm(formFromClient(client));
    setError('');
    setSuccess('');
  }

  function updateClientForm(field: ClientFormField, value: string) {
    setClientForm((current) => ({ ...current, [field]: value }));
  }

  async function handleClientSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      return;
    }

    setError('');
    setSuccess('');
    setIsSavingClient(true);

    try {
      const payload = normalizeClientPayload(clientForm);
      const savedClient = selectedClient
        ? await updateClient(token, selectedClient.id, payload)
        : await createClient(token, payload);

      setClients((current) => {
        if (selectedClient) {
          return current.map((client) => (client.id === savedClient.id ? savedClient : client));
        }
        return [...current, savedClient];
      });
      setSelectedClientId(savedClient.id);
      setClientForm(formFromClient(savedClient));
      setSuccess(selectedClient ? 'Client mis à jour.' : 'Client ajouté.');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Enregistrement du client impossible');
    } finally {
      setIsSavingClient(false);
    }
  }

  if (token && user) {
    return (
      <main className="page-shell dashboard" aria-label="Gestion des clients FacNor">
        <section className="card dashboard-header">
          <div>
            <p className="eyebrow">Clients</p>
            <h1>Bienvenue, {user.full_name}</h1>
            <p className="muted">
              Gérez les clients associés au compte <strong>{user.email}</strong>.
            </p>
          </div>
          <button className="secondary" onClick={logout}>Se déconnecter</button>
        </section>

        <section className="clients-layout">
          <aside className="card clients-list" aria-label="Liste des clients">
            <div className="section-title">
              <div>
                <p className="eyebrow">Portefeuille</p>
                <h2>{clients.length} client{clients.length > 1 ? 's' : ''}</h2>
              </div>
              <button type="button" onClick={startNewClient}>Nouveau</button>
            </div>

            {clients.length === 0 ? (
              <p className="muted">Aucun client pour le moment. Ajoutez votre premier client.</p>
            ) : (
              <ul>
                {clients.map((client) => (
                  <li key={client.id}>
                    <button
                      className={client.id === selectedClientId ? 'client-row active' : 'client-row'}
                      type="button"
                      onClick={() => selectClient(client)}
                    >
                      <strong>{client.name}</strong>
                      <span>{client.postal_code} {client.city}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </aside>

          <form className="card client-form" onSubmit={handleClientSubmit}>
            <div className="section-title">
              <div>
                <p className="eyebrow">{selectedClient ? 'Modification' : 'Création'}</p>
                <h2>{selectedClient ? selectedClient.name : 'Nouveau client'}</h2>
              </div>
            </div>

            <div className="form-grid">
              <label>
                Nom ou raison sociale
                <input value={clientForm.name} onChange={(event) => updateClientForm('name', event.target.value)} required />
              </label>
              <label>
                E-mail
                <input type="email" value={clientForm.email ?? ''} onChange={(event) => updateClientForm('email', event.target.value)} />
              </label>
              <label className="full-width">
                Adresse
                <input value={clientForm.address} onChange={(event) => updateClientForm('address', event.target.value)} required />
              </label>
              <label>
                Code postal
                <input value={clientForm.postal_code} onChange={(event) => updateClientForm('postal_code', event.target.value)} required />
              </label>
              <label>
                Ville
                <input value={clientForm.city} onChange={(event) => updateClientForm('city', event.target.value)} required />
              </label>
              <label>
                Pays
                <input value={clientForm.country} onChange={(event) => updateClientForm('country', event.target.value)} required />
              </label>
              <label>
                SIREN
                <input
                  inputMode="numeric"
                  maxLength={9}
                  pattern="[0-9]{9}"
                  placeholder="123456789"
                  value={clientForm.siren ?? ''}
                  onChange={(event) => updateClientForm('siren', event.target.value)}
                />
              </label>
              <label>
                N° TVA intracommunautaire
                <input
                  placeholder="FRAB123456789"
                  value={clientForm.vat_number ?? ''}
                  onChange={(event) => updateClientForm('vat_number', event.target.value.toUpperCase())}
                />
              </label>
            </div>

            {error && <p className="error" role="alert">{error}</p>}
            {success && <p className="success" role="status">{success}</p>}

            <div className="form-actions">
              <button type="submit" disabled={isSavingClient}>
                {isSavingClient ? 'Enregistrement…' : selectedClient ? 'Mettre à jour' : 'Ajouter le client'}
              </button>
              {selectedClient && <button className="secondary" type="button" onClick={startNewClient}>Annuler</button>}
            </div>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">FacNor</p>
        <h1>Gestion de factures normalisées</h1>
        <p>Connectez-vous pour accéder à votre tableau de bord et gérer vos clients.</p>
      </section>
      <form className="card login-form" onSubmit={handleLogin}>
        <h2>Connexion</h2>
        <label>
          Adresse e-mail
          <input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>
        <label>
          Mot de passe
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Connexion…' : 'Se connecter'}
        </button>
      </form>
    </main>
  );
}

export default App;
