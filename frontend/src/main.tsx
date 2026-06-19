import React, { FormEvent, useEffect, useState } from 'react';
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

const AUTH_TOKEN_KEY = 'facnor.authToken';
const AUTH_USER_KEY = 'facnor.authUser';

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
  return (
    <main className="dashboard-shell">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">Tableau de bord</p>
          <h1>Bienvenue, {user.company_name}</h1>
          <p className="lead">Vous êtes connecté à votre espace de facturation normalisée.</p>
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
          <span className="summary-label">TVA intracommunautaire</span>
          <strong>{user.vat_number ?? 'Non renseignée'}</strong>
        </article>
      </section>

      <section className="status-panel" role="status">
        <span className="status-dot" aria-hidden="true" />
        Session active — vous pouvez poursuivre vers la gestion des clients et factures.
      </section>
    </main>
  );
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
