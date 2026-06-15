import { FormEvent, useEffect, useState } from 'react';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
const storedToken = 'facnor.authToken';

type ApiStatus = 'idle' | 'loading' | 'ready' | 'error';
type ClientType = 'B2B' | 'B2C';

type Client = {
  id: number;
  client_type: ClientType;
  name: string;
  email: string | null;
  phone: string | null;
  address_line1: string;
  address_line2: string | null;
  postal_code: string;
  city: string;
  country: string;
  siren: string | null;
  vat_number: string | null;
  contact_full_name: string | null;
};

type ClientForm = {
  client_type: ClientType;
  name: string;
  email: string;
  phone: string;
  address_line1: string;
  address_line2: string;
  postal_code: string;
  city: string;
  country: string;
  siren: string;
  vat_number: string;
  contact_full_name: string;
};

const emptyClientForm: ClientForm = {
  client_type: 'B2B',
  name: '',
  email: '',
  phone: '',
  address_line1: '',
  address_line2: '',
  postal_code: '',
  city: '',
  country: 'France',
  siren: '',
  vat_number: '',
  contact_full_name: '',
};

function optionalText(value: string) {
  const trimmed = value.trim();
  return trimmed === '' ? null : trimmed;
}

function clientPayload(form: ClientForm) {
  return {
    client_type: form.client_type,
    name: form.name.trim(),
    email: optionalText(form.email),
    phone: optionalText(form.phone),
    address_line1: form.address_line1.trim(),
    address_line2: optionalText(form.address_line2),
    postal_code: form.postal_code.trim(),
    city: form.city.trim(),
    country: form.country.trim() || 'France',
    siren: form.client_type === 'B2B' ? optionalText(form.siren) : null,
    vat_number: form.client_type === 'B2B' ? optionalText(form.vat_number) : null,
    contact_full_name: optionalText(form.contact_full_name),
  };
}

export function App() {
  const [status, setStatus] = useState<ApiStatus>('idle');
  const [message, setMessage] = useState('Connexion à l’API en attente.');
  const [authMode, setAuthMode] = useState<'login' | 'register'>('register');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState(() => localStorage.getItem(storedToken) ?? '');
  const [clients, setClients] = useState<Client[]>([]);
  const [clientForm, setClientForm] = useState<ClientForm>(emptyClientForm);
  const [clientStatus, setClientStatus] = useState('Connectez-vous pour charger vos clients.');
  const isAuthenticated = token !== '';

  async function apiRequest<T>(path: string, options: RequestInit = {}) {
    const headers = new Headers(options.headers);
    headers.set('Content-Type', 'application/json');
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    const response = await fetch(`${apiBaseUrl}${path}`, { ...options, headers });
    if (!response.ok) {
      const details = await response.json().catch(() => ({}));
      throw new Error(details.detail ?? `Erreur API (${response.status})`);
    }
    return (await response.json()) as T;
  }

  async function loadClients() {
    if (!token) {
      return;
    }
    setClientStatus('Chargement des clients…');
    try {
      const payload = await apiRequest<Client[]>('/clients');
      setClients(payload);
      setClientStatus(payload.length === 0 ? 'Aucun client enregistré.' : `${payload.length} client(s) chargé(s).`);
    } catch (error) {
      setClientStatus(error instanceof Error ? error.message : 'Impossible de charger les clients.');
    }
  }

  useEffect(() => {
    const controller = new AbortController();

    async function loadHealth() {
      setStatus('loading');
      try {
        const response = await fetch(`${apiBaseUrl}/health`, { signal: controller.signal });
        if (!response.ok) {
          throw new Error(`Réponse API invalide (${response.status})`);
        }
        const payload = (await response.json()) as { status?: string };
        setStatus('ready');
        setMessage(payload.status === 'ok' ? 'API FacNor opérationnelle.' : 'API joignable.');
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') {
          return;
        }
        setStatus('error');
        setMessage('API indisponible pour le moment. Vérifiez VITE_API_BASE_URL.');
      }
    }

    loadHealth();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    loadClients();
  }, [token]);

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setClientStatus('Authentification en cours…');
    try {
      const payload = await apiRequest<{ access_token: string }>(`/auth/${authMode}`, {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem(storedToken, payload.access_token);
      setToken(payload.access_token);
      setPassword('');
      setClientStatus('Authentification réussie.');
    } catch (error) {
      setClientStatus(error instanceof Error ? error.message : 'Authentification impossible.');
    }
  }

  async function submitClient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setClientStatus('Création du client…');
    try {
      const created = await apiRequest<Client>('/clients', {
        method: 'POST',
        body: JSON.stringify(clientPayload(clientForm)),
      });
      setClients((current) => [...current, created].sort((left, right) => left.name.localeCompare(right.name)));
      setClientForm({ ...emptyClientForm, client_type: clientForm.client_type });
      setClientStatus(`Client « ${created.name} » créé.`);
    } catch (error) {
      setClientStatus(error instanceof Error ? error.message : 'Création du client impossible.');
    }
  }

  function logout() {
    localStorage.removeItem(storedToken);
    setToken('');
    setClients([]);
    setClientStatus('Connectez-vous pour charger vos clients.');
  }

  return (
    <main className="app-shell">
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">Facturation électronique française</p>
        <h1 id="page-title">FacNor</h1>
        <p className="intro">
          Gérez vos clients et préparez des factures normalisées avec numérotation,
          TVA et mentions légales obligatoires.
        </p>
        <dl className="api-card">
          <div>
            <dt>API configurée</dt>
            <dd>{apiBaseUrl}</dd>
          </div>
          <div>
            <dt>État</dt>
            <dd data-status={status}>{message}</dd>
          </div>
        </dl>
      </section>

      <section className="panel" aria-labelledby="auth-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Compte utilisateur</p>
            <h2 id="auth-title">Accès sécurisé</h2>
          </div>
          {isAuthenticated && <button onClick={logout}>Se déconnecter</button>}
        </div>
        {!isAuthenticated && (
          <form className="form-grid" onSubmit={submitAuth}>
            <label>
              Mode
              <select value={authMode} onChange={(event) => setAuthMode(event.target.value as 'login' | 'register')}>
                <option value="register">Créer un compte</option>
                <option value="login">Se connecter</option>
              </select>
            </label>
            <label>
              Email
              <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
            </label>
            <label>
              Mot de passe
              <input
                type="password"
                value={password}
                minLength={8}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>
            <button type="submit">Valider</button>
          </form>
        )}
      </section>

      <section className="panel" aria-labelledby="clients-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Gestion des clients</p>
            <h2 id="clients-title">Clients</h2>
          </div>
          <button type="button" onClick={loadClients} disabled={!isAuthenticated}>
            Actualiser
          </button>
        </div>
        <p className="status-line">{clientStatus}</p>

        <form className="client-form" onSubmit={submitClient}>
          <label>
            Type
            <select
              value={clientForm.client_type}
              onChange={(event) => setClientForm({ ...clientForm, client_type: event.target.value as ClientType })}
              disabled={!isAuthenticated}
            >
              <option value="B2B">Professionnel (B2B)</option>
              <option value="B2C">Particulier (B2C)</option>
            </select>
          </label>
          <label>
            Nom
            <input
              value={clientForm.name}
              onChange={(event) => setClientForm({ ...clientForm, name: event.target.value })}
              disabled={!isAuthenticated}
              required
            />
          </label>
          <label>
            Email
            <input
              type="email"
              value={clientForm.email}
              onChange={(event) => setClientForm({ ...clientForm, email: event.target.value })}
              disabled={!isAuthenticated}
            />
          </label>
          <label>
            Téléphone
            <input
              value={clientForm.phone}
              onChange={(event) => setClientForm({ ...clientForm, phone: event.target.value })}
              disabled={!isAuthenticated}
            />
          </label>
          <label className="wide">
            Adresse
            <input
              value={clientForm.address_line1}
              onChange={(event) => setClientForm({ ...clientForm, address_line1: event.target.value })}
              disabled={!isAuthenticated}
              required
            />
          </label>
          <label>
            Code postal
            <input
              value={clientForm.postal_code}
              onChange={(event) => setClientForm({ ...clientForm, postal_code: event.target.value })}
              disabled={!isAuthenticated}
              required
            />
          </label>
          <label>
            Ville
            <input
              value={clientForm.city}
              onChange={(event) => setClientForm({ ...clientForm, city: event.target.value })}
              disabled={!isAuthenticated}
              required
            />
          </label>
          <label>
            Pays
            <input
              value={clientForm.country}
              onChange={(event) => setClientForm({ ...clientForm, country: event.target.value })}
              disabled={!isAuthenticated}
              required
            />
          </label>
          {clientForm.client_type === 'B2B' && (
            <>
              <label>
                SIREN
                <input
                  value={clientForm.siren}
                  pattern="[0-9]{9}"
                  onChange={(event) => setClientForm({ ...clientForm, siren: event.target.value })}
                  disabled={!isAuthenticated}
                  required
                />
              </label>
              <label>
                TVA intracommunautaire
                <input
                  value={clientForm.vat_number}
                  onChange={(event) => setClientForm({ ...clientForm, vat_number: event.target.value })}
                  disabled={!isAuthenticated}
                />
              </label>
            </>
          )}
          <label className="wide">
            Contact
            <input
              value={clientForm.contact_full_name}
              onChange={(event) => setClientForm({ ...clientForm, contact_full_name: event.target.value })}
              disabled={!isAuthenticated}
            />
          </label>
          <button type="submit" disabled={!isAuthenticated}>
            Créer le client
          </button>
        </form>

        <div className="client-list" aria-live="polite">
          {clients.map((client) => (
            <article className="client-card" key={client.id}>
              <div>
                <strong>{client.name}</strong>
                <span>{client.client_type}</span>
              </div>
              <p>
                {client.address_line1}, {client.postal_code} {client.city}, {client.country}
              </p>
              {(client.email || client.phone) && <p>{[client.email, client.phone].filter(Boolean).join(' · ')}</p>}
              {client.siren && <p>SIREN : {client.siren}</p>}
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
