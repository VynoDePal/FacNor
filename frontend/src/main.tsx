import React, { FormEvent, useEffect, useMemo, useState } from 'react';
import ReactDOM from 'react-dom/client';
import './styles.css';

type AuthUser = {
  id: number;
  email: string;
  company_name: string;
  siren: string | null;
  vat_number: string | null;
  address: string;
};

type LoginResponse = {
  access_token: string;
  token_type: 'bearer';
  user: AuthUser;
};

type ClientType = 'business' | 'individual';

type Client = {
  id: number;
  name: string;
  email: string | null;
  client_type: ClientType;
  siren: string | null;
  vat_number: string | null;
  address: string;
};

type ClientFormState = {
  name: string;
  email: string;
  client_type: ClientType;
  siren: string;
  vat_number: string;
  address: string;
};

const AUTH_TOKEN_KEY = 'facnor.authToken';
const AUTH_USER_KEY = 'facnor.authUser';

const EMPTY_CLIENT_FORM: ClientFormState = {
  name: '',
  email: '',
  client_type: 'business',
  siren: '',
  vat_number: '',
  address: '',
};

function App() {
  const [user, setUser] = useState<AuthUser | null>(() => readStoredUser());
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (user) {
      window.history.replaceState(null, '', '/dashboard');
    }
  }, [user]);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        throw new Error(response.status === 401 ? 'Identifiants invalides.' : 'Connexion impossible pour le moment.');
      }

      const data = (await response.json()) as LoginResponse;
      localStorage.setItem(AUTH_TOKEN_KEY, data.access_token);
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(data.user));
      setUser(data.user);
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : 'Une erreur inattendue est survenue.');
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    setUser(null);
    setPassword('');
    window.history.replaceState(null, '', '/');
  }

  if (user) {
    return <Dashboard user={user} onLogout={handleLogout} />;
  }

  return (
    <main className="app-shell auth-page">
      <section className="hero auth-intro" aria-labelledby="page-title">
        <p className="eyebrow">FacNor</p>
        <h1 id="page-title">Connexion à votre facturation</h1>
        <p className="lead">
          Accédez à votre espace sécurisé pour gérer vos clients, préparer vos factures
          normalisées et suivre votre activité.
        </p>
      </section>

      <section className="auth-card" aria-labelledby="login-title">
        <div>
          <p className="eyebrow">Authentification</p>
          <h2 id="login-title">Se connecter</h2>
          <p className="form-help">Utilisez l'adresse e-mail et le mot de passe de votre compte FacNor.</p>
        </div>

        <form className="login-form" onSubmit={handleLogin}>
          <label>
            Adresse e-mail
            <input
              autoComplete="email"
              name="email"
              onChange={(event) => setEmail(event.target.value)}
              placeholder="vous@entreprise.fr"
              required
              type="email"
              value={email}
            />
          </label>

          <label>
            Mot de passe
            <input
              autoComplete="current-password"
              minLength={8}
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              required
              type="password"
              value={password}
            />
          </label>

          {error ? <p className="form-error" role="alert">{error}</p> : null}

          <button className="primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? 'Connexion…' : 'Se connecter'}
          </button>
        </form>
      </section>
    </main>
  );
}

function Dashboard({ user, onLogout }: { user: AuthUser; onLogout: () => void }) {
  const [clients, setClients] = useState<Client[]>([]);
  const [form, setForm] = useState<ClientFormState>(EMPTY_CLIENT_FORM);
  const [editingClientId, setEditingClientId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const editingClient = useMemo(
    () => clients.find((client) => client.id === editingClientId) ?? null,
    [clients, editingClientId],
  );

  useEffect(() => {
    void loadClients();
  }, []);

  async function requestClients(path = '', options: RequestInit = {}) {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    const response = await fetch(`/api/clients${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        ...options.headers,
      },
    });

    if (response.status === 401) {
      onLogout();
      throw new Error('Votre session a expiré. Veuillez vous reconnecter.');
    }

    return response;
  }

  async function loadClients() {
    setIsLoading(true);
    setError('');

    try {
      const response = await requestClients();
      if (!response.ok) {
        throw new Error('Impossible de charger les clients.');
      }
      setClients((await response.json()) as Client[]);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Une erreur inattendue est survenue.');
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setMessage('');
    setIsSaving(true);

    try {
      const payload = toClientPayload(form);
      const response = await requestClients(editingClientId ? `/${editingClientId}` : '', {
        method: editingClientId ? 'PUT' : 'POST',
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(await clientErrorMessage(response));
      }

      const savedClient = (await response.json()) as Client;
      setClients((currentClients) => {
        if (editingClientId) {
          return currentClients.map((client) => (client.id === savedClient.id ? savedClient : client));
        }
        return [...currentClients, savedClient].sort((first, second) => first.name.localeCompare(second.name));
      });
      setMessage(editingClientId ? 'Client modifié avec succès.' : 'Client créé avec succès.');
      resetForm();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Une erreur inattendue est survenue.');
    } finally {
      setIsSaving(false);
    }
  }

  function startEditing(client: Client) {
    setEditingClientId(client.id);
    setForm({
      name: client.name,
      email: client.email ?? '',
      client_type: client.client_type,
      siren: client.siren ?? '',
      vat_number: client.vat_number ?? '',
      address: client.address,
    });
    setError('');
    setMessage('');
  }

  function resetForm() {
    setEditingClientId(null);
    setForm(EMPTY_CLIENT_FORM);
  }

  return (
    <main className="dashboard-shell">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">Tableau de bord</p>
          <h1>Bienvenue, {user.company_name}</h1>
          <p className="lead">Créez et modifiez vos fiches clients B2B ou B2C depuis votre espace sécurisé.</p>
        </div>
        <button className="secondary-button" onClick={onLogout} type="button">
          Se déconnecter
        </button>
      </header>

      <section className="dashboard-grid" aria-label="Résumé du compte">
        <article className="summary-card">
          <span className="summary-label">Compte</span>
          <strong>{user.email}</strong>
        </article>
        <article className="summary-card">
          <span className="summary-label">SIREN</span>
          <strong>{user.siren ?? 'Non renseigné'}</strong>
        </article>
        <article className="summary-card">
          <span className="summary-label">Clients</span>
          <strong>{clients.length}</strong>
        </article>
      </section>

      <section className="clients-layout" aria-labelledby="clients-title">
        <div className="client-form-card">
          <p className="eyebrow">Gestion des clients</p>
          <h2 id="clients-title">{editingClient ? `Modifier ${editingClient.name}` : 'Nouveau client'}</h2>
          <p className="form-help">Les champs nom, type et adresse sont obligatoires. Le SIREN doit contenir 9 chiffres.</p>

          <form className="client-form" onSubmit={handleSubmit}>
            <label>
              Nom ou raison sociale
              <input
                name="name"
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                placeholder="Ex. Dupont SAS"
                required
                value={form.name}
              />
            </label>

            <label>
              Type de client
              <select
                name="client_type"
                onChange={(event) => setForm({ ...form, client_type: event.target.value as ClientType })}
                value={form.client_type}
              >
                <option value="business">Professionnel (B2B)</option>
                <option value="individual">Particulier (B2C)</option>
              </select>
            </label>

            <label>
              Adresse e-mail
              <input
                name="email"
                onChange={(event) => setForm({ ...form, email: event.target.value })}
                placeholder="client@example.fr"
                type="email"
                value={form.email}
              />
            </label>

            <div className="form-row">
              <label>
                SIREN
                <input
                  inputMode="numeric"
                  maxLength={9}
                  minLength={9}
                  name="siren"
                  onChange={(event) => setForm({ ...form, siren: event.target.value.replace(/\D/g, '') })}
                  pattern="\d{9}"
                  placeholder="123456789"
                  value={form.siren}
                />
              </label>

              <label>
                TVA intracommunautaire
                <input
                  name="vat_number"
                  onChange={(event) => setForm({ ...form, vat_number: event.target.value })}
                  placeholder="FR00123456789"
                  value={form.vat_number}
                />
              </label>
            </div>

            <label>
              Adresse de facturation
              <textarea
                name="address"
                onChange={(event) => setForm({ ...form, address: event.target.value })}
                placeholder="12 rue de la Paix, 75002 Paris"
                required
                rows={4}
                value={form.address}
              />
            </label>

            {error ? <p className="form-error" role="alert">{error}</p> : null}
            {message ? <p className="form-success" role="status">{message}</p> : null}

            <div className="form-actions">
              <button className="primary-button" disabled={isSaving} type="submit">
                {isSaving ? 'Enregistrement…' : editingClient ? 'Enregistrer les modifications' : 'Créer le client'}
              </button>
              {editingClient ? (
                <button className="secondary-button" onClick={resetForm} type="button">
                  Annuler
                </button>
              ) : null}
            </div>
          </form>
        </div>

        <div className="clients-list-card">
          <div className="list-header">
            <div>
              <p className="eyebrow">Répertoire</p>
              <h2>Clients enregistrés</h2>
            </div>
            <button className="secondary-button" disabled={isLoading} onClick={loadClients} type="button">
              Actualiser
            </button>
          </div>

          {isLoading ? <p className="empty-state">Chargement des clients…</p> : null}
          {!isLoading && clients.length === 0 ? <p className="empty-state">Aucun client pour le moment.</p> : null}
          {!isLoading && clients.length > 0 ? (
            <div className="clients-list">
              {clients.map((client) => (
                <article className="client-card" key={client.id}>
                  <div>
                    <span className="client-type">{client.client_type === 'business' ? 'B2B' : 'B2C'}</span>
                    <h3>{client.name}</h3>
                    <p>{client.address}</p>
                  </div>
                  <dl>
                    <div>
                      <dt>Email</dt>
                      <dd>{client.email ?? 'Non renseigné'}</dd>
                    </div>
                    <div>
                      <dt>SIREN</dt>
                      <dd>{client.siren ?? 'Non renseigné'}</dd>
                    </div>
                    <div>
                      <dt>TVA</dt>
                      <dd>{client.vat_number ?? 'Non renseignée'}</dd>
                    </div>
                  </dl>
                  <button className="secondary-button" onClick={() => startEditing(client)} type="button">
                    Modifier
                  </button>
                </article>
              ))}
            </div>
          ) : null}
        </div>
      </section>
    </main>
  );
}

function toClientPayload(form: ClientFormState) {
  return {
    name: form.name.trim(),
    email: optionalString(form.email),
    client_type: form.client_type,
    siren: optionalString(form.siren),
    vat_number: optionalString(form.vat_number),
    address: form.address.trim(),
  };
}

function optionalString(value: string) {
  const trimmedValue = value.trim();
  return trimmedValue.length > 0 ? trimmedValue : null;
}

async function clientErrorMessage(response: Response) {
  if (response.status === 422) {
    return 'Certains champs sont invalides. Vérifiez le format de l’e-mail et du SIREN.';
  }

  try {
    const data = (await response.json()) as { detail?: string };
    return data.detail ?? 'Impossible d’enregistrer ce client.';
  } catch {
    return 'Impossible d’enregistrer ce client.';
  }
}

function readStoredUser(): AuthUser | null {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  const storedUser = localStorage.getItem(AUTH_USER_KEY);

  if (!token || !storedUser) {
    return null;
  }

  try {
    return JSON.parse(storedUser) as AuthUser;
  } catch {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    return null;
  }
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
