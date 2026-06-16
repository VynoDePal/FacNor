import { FormEvent, useEffect, useState } from 'react';
import { AuthUser, fetchCurrentUser, login } from './api';
import './styles.css';

const TOKEN_STORAGE_KEY = 'facnor_access_token';

function App() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY));
  const [user, setUser] = useState<AuthUser | null>(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!token) {
      setUser(null);
      return;
    }

    fetchCurrentUser(token)
      .then(setUser)
      .catch(() => {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        setToken(null);
      });
  }, [token]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
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
    setPassword('');
  }

  if (token && user) {
    return (
      <main className="page-shell dashboard" aria-label="Tableau de bord FacNor">
        <section className="card">
          <p className="eyebrow">Tableau de bord</p>
          <h1>Bienvenue, {user.full_name}</h1>
          <p className="muted">
            Vous êtes connecté à FacNor avec le compte <strong>{user.email}</strong>.
          </p>
          <div className="dashboard-grid">
            <article>
              <span>Factures</span>
              <strong>Prêtes à créer</strong>
            </article>
            <article>
              <span>Clients</span>
              <strong>API sécurisée</strong>
            </article>
          </div>
          <button className="secondary" onClick={logout}>Se déconnecter</button>
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
      <form className="card login-form" onSubmit={handleSubmit}>
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
