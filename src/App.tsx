import { useEffect, useState } from 'react';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

type ApiStatus = 'idle' | 'loading' | 'ready' | 'error';

export function App() {
  const [status, setStatus] = useState<ApiStatus>('idle');
  const [message, setMessage] = useState('Connexion à l’API en attente.');

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
    </main>
  );
}
