import { FormEvent, useEffect, useState } from 'react';
import { AuthResponse, User, fetchHealth, getApiBaseUrl, login } from './api';
import './styles.css';

type ApiState = 'loading' | 'online' | 'offline';

type View = 'login' | 'dashboard';

const TOKEN_STORAGE_KEY = 'facnor_access_token';
const USER_STORAGE_KEY = 'facnor_user';

function readStoredUser(): User | null {
  const rawUser = window.localStorage.getItem(USER_STORAGE_KEY);
  if (!rawUser) {
    return null;
  }

  try {
    return JSON.parse(rawUser) as User;
  } catch {
    window.localStorage.removeItem(USER_STORAGE_KEY);
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    return null;
  }
}

export function App() {
  const [apiState, setApiState] = useState<ApiState>('loading');
  const [message, setMessage] = useState('Connexion à l’API FacNor…');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentUser, setCurrentUser] = useState<User | null>(() => readStoredUser());
  const [view, setView] = useState<View>(() => (window.localStorage.getItem(TOKEN_STORAGE_KEY) ? 'dashboard' : 'login'));

  useEffect(() => {
    fetchHealth()
      .then((health) => {
        setApiState('online');
        setMessage(health.status === 'ok' ? 'API connectée' : `Statut API : ${health.status}`);
      })
      .catch((error: unknown) => {
        setApiState('offline');
        setMessage(error instanceof Error ? error.message : 'API FacNor indisponible');
      });
  }, []);

  function storeSession(auth: AuthResponse) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, auth.access_token);
    window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(auth.user));
    setCurrentUser(auth.user);
    setView('dashboard');
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthError('');
    setIsSubmitting(true);

    try {
      const auth = await login({ email, password });
      storeSession(auth);
    } catch (error: unknown) {
      setAuthError(error instanceof Error ? error.message : 'Connexion impossible.');
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleLogout() {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    window.localStorage.removeItem(USER_STORAGE_KEY);
    setCurrentUser(null);
    setPassword('');
    setView('login');
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">FacNor</p>
        <h1>Gestion de factures normalisées</h1>
        <p className="lede">
          Connectez-vous pour accéder au tableau de bord de gestion des factures normalisées.
        </p>
      </section>

      <section className="status-card" aria-live="polite">
        <span className={`status-dot status-dot--${apiState}`} />
        <div>
          <h2>Connexion backend</h2>
          <p>{message}</p>
          <small>Base API : {getApiBaseUrl()}</small>
        </div>
      </section>

      {view === 'login' ? (
        <section className="auth-card" aria-labelledby="login-title">
          <div>
            <p className="eyebrow">Authentification</p>
            <h2 id="login-title">Connexion utilisateur</h2>
            <p className="muted">Utilisez votre compte FacNor pour poursuivre vers le tableau de bord.</p>
          </div>

          <form className="auth-form" onSubmit={handleLogin}>
            <label>
              Email
              <input
                autoComplete="email"
                name="email"
                onChange={(event) => setEmail(event.target.value)}
                placeholder="marie@example.com"
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
                placeholder="Votre mot de passe"
                required
                type="password"
                value={password}
              />
            </label>

            {authError ? (
              <p className="form-error" role="alert">
                {authError}
              </p>
            ) : null}

            <button disabled={isSubmitting || apiState === 'offline'} type="submit">
              {isSubmitting ? 'Connexion…' : 'Se connecter'}
            </button>
          </form>
        </section>
      ) : (
        <section className="dashboard-card" aria-labelledby="dashboard-title">
          <div>
            <p className="eyebrow">Tableau de bord</p>
            <h2 id="dashboard-title">Bienvenue{currentUser?.full_name ? `, ${currentUser.full_name}` : ''}</h2>
            <p className="muted">
              Vous êtes connecté avec le compte <strong>{currentUser?.email}</strong>. Vous pouvez maintenant gérer vos clients et factures.
            </p>
          </div>
          <button className="secondary-button" type="button" onClick={handleLogout}>
            Se déconnecter
          </button>
        </section>
      )}
    </main>
  );
}
