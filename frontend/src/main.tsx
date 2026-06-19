import React from 'react';
import ReactDOM from 'react-dom/client';
import './styles.css';

function App() {
  return (
    <main className="app-shell">
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">FacNor</p>
        <h1 id="page-title">Gestion de factures normalisées</h1>
        <p className="lead">
          Une base frontend TypeScript est prête pour construire l'interface de
          facturation conforme aux exigences françaises.
        </p>
        <div className="status-card" role="status">
          <span className="status-dot" aria-hidden="true" />
          Application frontend lancée
        </div>
      </section>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
