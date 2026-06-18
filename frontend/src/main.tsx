import React, { FormEvent, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { API_BASE_URL, AuthResponse, login, register } from './api';
import './styles.css';

const TOKEN_STORAGE_KEY = 'facnor_access_token';

type View = 'login' | 'register' | 'dashboard';

function getInitialView(): View {
  return localStorage.getItem(TOKEN_STORAGE_KEY) ? 'dashboard' : 'login';
}

function App() {
  const [view, setView] = useState<View>(getInitialView);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_STORAGE_KEY));
  const [userEmail, setUserEmail] = useState<string | null>(() => localStorage.getItem('facnor_user_email'));

  useEffect(() => {
    window.history.replaceState(null, '', view === 'dashboard' ? '/dashboard' : '/');
  }, [view]);

  function handleAuthenticated(response: AuthResponse) {
    localStorage.setItem(TOKEN_STORAGE_KEY, response.access_token);
    if (response.email) {
      localStorage.setItem('facnor_user_email', response.email);
      setUserEmail(response.email);
    }
    setToken(response.access_token);
    setView('dashboard');
  }

  function logout() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem('facnor_user_email');
    setToken(null);
    setUserEmail(null);
    setView('login');
  }

  if (view === 'dashboard' && token) {
    return <Dashboard apiUrl={API_BASE_URL} email={userEmail} onLogout={logout} />;
  }

  return (
    <main className="auth-shell">
      <section className="hero-card">
        <p className="eyebrow">FacNor</p>
        <h1>Gérez vos factures normalisées en toute confiance.</h1>
        <p>
          Connectez-vous à votre espace pour retrouver vos clients, préparer vos factures et suivre votre activité.
        </p>
      </section>
      <section className="auth-card">
        <div className="tabs" role="tablist" aria-label="Choix du formulaire">
          <button className={view === 'login' ? 'active' : ''} onClick={() => setView('login')} type="button">
            Connexion
          </button>
          <button className={view === 'register' ? 'active' : ''} onClick={() => setView('register')} type="button">
            Créer un compte
          </button>
        </div>
        {view === 'register' ? (
          <RegisterForm onAuthenticated={handleAuthenticated} />
        ) : (
          <LoginForm onAuthenticated={handleAuthenticated} />
        )}
      </section>
    </main>
  );
}

function LoginForm({ onAuthenticated }: { onAuthenticated: (response: AuthResponse) => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      onAuthenticated(await login({ email, password }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connexion impossible.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="auth-form">
      <h2>Connexion</h2>
      <label>
        Email
        <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
      </label>
      <label>
        Mot de passe
        <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
      </label>
      {error && <p className="error" role="alert">{error}</p>}
      <button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Connexion...' : 'Se connecter'}</button>
    </form>
  );
}

function RegisterForm({ onAuthenticated }: { onAuthenticated: (response: AuthResponse) => void }) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      onAuthenticated(await register({ full_name: fullName, email, password }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Création de compte impossible.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="auth-form">
      <h2>Créer un compte</h2>
      <label>
        Nom complet
        <input value={fullName} onChange={(event) => setFullName(event.target.value)} required />
      </label>
      <label>
        Email
        <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
      </label>
      <label>
        Mot de passe
        <input type="password" minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} required />
      </label>
      {error && <p className="error" role="alert">{error}</p>}
      <button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Création...' : 'Créer mon compte'}</button>
    </form>
  );
}

function Dashboard({ apiUrl, email, onLogout }: { apiUrl: string; email: string | null; onLogout: () => void }) {
  return (
    <main className="dashboard">
      <nav>
        <strong>FacNor</strong>
        <button type="button" onClick={onLogout}>Déconnexion</button>
      </nav>
      <section>
        <p className="eyebrow">Tableau de bord</p>
        <h1>Bienvenue{email ? `, ${email}` : ''}</h1>
        <p>Vous êtes connecté. Les prochains modules clients et factures utiliseront ce jeton d’authentification.</p>
        <div className="info-card">
          <span>API configurée</span>
          <code>{apiUrl}</code>
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
