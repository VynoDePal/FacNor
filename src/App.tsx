import { useEffect, useState } from 'react';
import { fetchHealth, getApiBaseUrl } from './api';
import './styles.css';

type ApiState = 'loading' | 'online' | 'offline';

export function App() {
  const [apiState, setApiState] = useState<ApiState>('loading');
  const [message, setMessage] = useState('Connexion à l’API FacNor…');

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

  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">FacNor</p>
        <h1>Gestion de factures normalisées</h1>
        <p className="lede">
          Interface frontend TypeScript prête à consommer l’API REST du backend FacNor.
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
    </main>
  );
}
