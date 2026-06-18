import React, { FormEvent, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { API_BASE_URL, AuthResponse, Client, ClientPayload, Invoice, InvoiceLinePayload, InvoicePayload, createClient, createInvoice, deleteClient, getHealth, listClients, listInvoices, login, register, updateClient } from './api';
import './styles.css';

const TOKEN_STORAGE_KEY = 'facnor_access_token';
const emptyClientForm: ClientPayload = { client_type: 'b2c', name: '', email: '', address: '', siren: '', vat_number: '' };
const emptyInvoiceLine: InvoiceLinePayload = { description: '', quantity: 1, unit_price: 0, tax_rate: 20 };
const today = new Date().toISOString().slice(0, 10);
type View = 'login' | 'register' | 'dashboard';
type InvoiceFormState = { client_id: string; invoice_number: string; issue_date: string; due_date: string; lines: InvoiceLinePayload[] };

function getInitialView(): View {
  return localStorage.getItem(TOKEN_STORAGE_KEY) ? 'dashboard' : 'login';
}

function createEmptyInvoiceForm(clients: Client[] = []): InvoiceFormState {
  return { client_id: clients[0]?.id.toString() ?? '', invoice_number: '', issue_date: today, due_date: '', lines: [{ ...emptyInvoiceLine }] };
}

function roundAmount(value: number): number {
  return Math.round((value + Number.EPSILON) * 1000) / 1000;
}

function formatAmount(value: number): string {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(value);
}

function calculateInvoiceTotals(lines: InvoiceLinePayload[]) {
  const calculatedLines = lines.map((line) => {
    const lineTotalExcludingTax = roundAmount((Number.isFinite(line.quantity) ? line.quantity : 0) * (Number.isFinite(line.unit_price) ? line.unit_price : 0));
    const lineTotalTax = roundAmount(lineTotalExcludingTax * ((Number.isFinite(line.tax_rate) ? line.tax_rate : 0) / 100));
    return { ...line, lineTotalExcludingTax, lineTotalTax, lineTotalIncludingTax: roundAmount(lineTotalExcludingTax + lineTotalTax) };
  });
  return {
    lines: calculatedLines,
    totalExcludingTax: roundAmount(calculatedLines.reduce((sum, line) => sum + line.lineTotalExcludingTax, 0)),
    totalTax: roundAmount(calculatedLines.reduce((sum, line) => sum + line.lineTotalTax, 0)),
    totalIncludingTax: roundAmount(calculatedLines.reduce((sum, line) => sum + line.lineTotalIncludingTax, 0)),
  };
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
    return <Dashboard apiUrl={API_BASE_URL} email={userEmail} token={token} onLogout={logout} />;
  }

  return (
    <main className="auth-shell">
      <section className="hero-card">
        <p className="eyebrow">FacNor</p>
        <h1>Gérez vos factures normalisées en toute confiance.</h1>
        <p>Connectez-vous à votre espace pour retrouver vos clients, préparer vos factures et suivre votre activité.</p>
      </section>
      <section className="auth-card">
        <div className="tabs" role="tablist" aria-label="Choix du formulaire">
          <button className={view === 'login' ? 'active' : ''} onClick={() => setView('login')} type="button">Connexion</button>
          <button className={view === 'register' ? 'active' : ''} onClick={() => setView('register')} type="button">Créer un compte</button>
        </div>
        {view === 'register' ? <RegisterForm onAuthenticated={handleAuthenticated} /> : <LoginForm onAuthenticated={handleAuthenticated} />}
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
      <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
      <label>Mot de passe<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
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
      <label>Nom complet<input value={fullName} onChange={(event) => setFullName(event.target.value)} required /></label>
      <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
      <label>Mot de passe<input type="password" minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
      {error && <p className="error" role="alert">{error}</p>}
      <button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Création...' : 'Créer mon compte'}</button>
    </form>
  );
}

function Dashboard({ apiUrl, email, token, onLogout }: { apiUrl: string; email: string | null; token: string; onLogout: () => void }) {
  const [apiStatus, setApiStatus] = useState('vérification...');
  const [clients, setClients] = useState<Client[]>([]);

  useEffect(() => {
    getHealth().then((health) => setApiStatus(health.status)).catch(() => setApiStatus('indisponible'));
  }, []);

  return (
    <main className="dashboard">
      <nav><strong>FacNor</strong><button type="button" onClick={onLogout}>Déconnexion</button></nav>
      <section className="dashboard-header">
        <p className="eyebrow">Tableau de bord</p>
        <h1>Bienvenue{email ? `, ${email}` : ''}</h1>
        <p>Créez, modifiez et supprimez vos clients avant de préparer leurs factures normalisées.</p>
        <div className="info-card"><span>API configurée</span><code>{apiUrl}</code><span>Statut backend : {apiStatus}</span></div>
      </section>
      <ClientsManager token={token} onClientsChange={setClients} />
      <InvoicesManager token={token} clients={clients} />
    </main>
  );
}

function ClientsManager({ token, onClientsChange }: { token: string; onClientsChange?: (clients: Client[]) => void }) {
  const [clients, setClients] = useState<Client[]>([]);
  const [form, setForm] = useState<ClientPayload>(emptyClientForm);
  const [editingClientId, setEditingClientId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isLoading, setLoading] = useState(true);
  const [isSubmitting, setSubmitting] = useState(false);
  const selectedClient = clients.find((client) => client.id === editingClientId) ?? null;

  useEffect(() => {
    refreshClients();
  }, [token]);

  useEffect(() => {
    onClientsChange?.(clients);
  }, [clients, onClientsChange]);

  async function refreshClients() {
    setError(null);
    setLoading(true);
    try {
      setClients(await listClients(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chargement des clients impossible.');
    } finally {
      setLoading(false);
    }
  }

  function updateField<K extends keyof ClientPayload>(field: K, value: ClientPayload[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function startEditing(client: Client) {
    setEditingClientId(client.id);
    setSuccess(null);
    setError(null);
    setForm({ client_type: client.client_type, name: client.name, email: client.email ?? '', address: client.address, siren: client.siren ?? '', vat_number: client.vat_number ?? '' });
  }

  function resetForm() {
    setEditingClientId(null);
    setForm(emptyClientForm);
  }

  function normalizePayload(payload: ClientPayload): ClientPayload {
    return {
      client_type: payload.client_type,
      name: payload.name.trim(),
      email: payload.email?.trim() || null,
      address: payload.address.trim(),
      siren: payload.client_type === 'b2b' ? payload.siren?.trim() || null : null,
      vat_number: payload.client_type === 'b2b' ? payload.vat_number?.trim() || null : null,
    };
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      const savedClient = editingClientId ? await updateClient(token, editingClientId, normalizePayload(form)) : await createClient(token, normalizePayload(form));
      setClients((current) => editingClientId ? current.map((client) => client.id === savedClient.id ? savedClient : client) : [...current, savedClient]);
      setSuccess(editingClientId ? 'Client modifié.' : 'Client créé.');
      resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Enregistrement du client impossible.');
    } finally {
      setSubmitting(false);
    }
  }

  async function removeClient(client: Client) {
    if (!window.confirm(`Supprimer le client ${client.name} ?`)) return;
    setError(null);
    setSuccess(null);
    try {
      await deleteClient(token, client.id);
      setClients((current) => current.filter((item) => item.id !== client.id));
      if (editingClientId === client.id) resetForm();
      setSuccess('Client supprimé.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Suppression du client impossible.');
    }
  }

  return (
    <section className="clients-panel" aria-labelledby="clients-title">
      <div className="section-heading">
        <div><p className="eyebrow">Gestion des clients</p><h2 id="clients-title">Clients</h2></div>
        <button type="button" className="secondary-button" onClick={refreshClients} disabled={isLoading}>Actualiser</button>
      </div>
      <form className="client-form" onSubmit={submit}>
        <h3>{selectedClient ? `Modifier ${selectedClient.name}` : 'Créer un client'}</h3>
        <div className="form-grid">
          <label>Type<select value={form.client_type} onChange={(event) => updateField('client_type', event.target.value as ClientPayload['client_type'])}><option value="b2c">Particulier (B2C)</option><option value="b2b">Entreprise (B2B)</option></select></label>
          <label>Nom<input value={form.name} onChange={(event) => updateField('name', event.target.value)} required /></label>
          <label>Email<input type="email" value={form.email ?? ''} onChange={(event) => updateField('email', event.target.value)} /></label>
          <label>Adresse<input value={form.address} onChange={(event) => updateField('address', event.target.value)} required /></label>
          {form.client_type === 'b2b' && <><label>SIREN<input value={form.siren ?? ''} onChange={(event) => updateField('siren', event.target.value)} required /></label><label>TVA intracommunautaire<input value={form.vat_number ?? ''} onChange={(event) => updateField('vat_number', event.target.value)} required /></label></>}
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        {success && <p className="success" role="status">{success}</p>}
        <div className="form-actions"><button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Enregistrement...' : selectedClient ? 'Modifier le client' : 'Créer le client'}</button>{selectedClient && <button type="button" className="secondary-button" onClick={resetForm}>Annuler</button>}</div>
      </form>
      <div className="clients-list">
        {isLoading ? <p>Chargement des clients...</p> : clients.length === 0 ? <p>Aucun client pour le moment. Créez votre premier client.</p> : clients.map((client) => (
          <article className="client-card" key={client.id}>
            <div><span className="badge">{client.client_type === 'b2b' ? 'Entreprise' : 'Particulier'}</span><h3>{client.name}</h3><p>{client.address}</p>{client.email && <p>{client.email}</p>}{client.client_type === 'b2b' && <p>SIREN {client.siren} · TVA {client.vat_number}</p>}</div>
            <div className="client-actions"><button type="button" className="secondary-button" onClick={() => startEditing(client)}>Modifier</button><button type="button" className="danger-button" onClick={() => removeClient(client)}>Supprimer</button></div>
          </article>
        ))}
      </div>
    </section>
  );
}

function InvoicesManager({ token, clients }: { token: string; clients: Client[] }) {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [form, setForm] = useState<InvoiceFormState>(() => createEmptyInvoiceForm(clients));
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isLoading, setLoading] = useState(true);
  const [isSubmitting, setSubmitting] = useState(false);
  const totals = useMemo(() => calculateInvoiceTotals(form.lines), [form.lines]);

  useEffect(() => {
    refreshInvoices();
  }, [token]);

  useEffect(() => {
    setForm((current) => current.client_id || clients.length === 0 ? current : { ...current, client_id: clients[0].id.toString() });
  }, [clients]);

  async function refreshInvoices() {
    setError(null);
    setLoading(true);
    try {
      setInvoices(await listInvoices(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chargement des factures impossible.');
    } finally {
      setLoading(false);
    }
  }

  function updateField<K extends keyof Omit<InvoiceFormState, 'lines'>>(field: K, value: InvoiceFormState[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateLine(index: number, field: keyof InvoiceLinePayload, value: string) {
    setForm((current) => ({
      ...current,
      lines: current.lines.map((line, lineIndex) => lineIndex === index ? { ...line, [field]: field === 'description' ? value : Number(value) } : line),
    }));
  }

  function addLine() {
    setForm((current) => ({ ...current, lines: [...current.lines, { ...emptyInvoiceLine }] }));
  }

  function removeLine(index: number) {
    setForm((current) => ({ ...current, lines: current.lines.length > 1 ? current.lines.filter((_, lineIndex) => lineIndex !== index) : current.lines }));
  }

  function buildPayload(): InvoicePayload {
    return {
      client_id: Number(form.client_id),
      invoice_number: form.invoice_number.trim() || null,
      issue_date: form.issue_date,
      due_date: form.due_date || null,
      lines: form.lines.map((line) => ({ description: line.description.trim(), quantity: line.quantity, unit_price: line.unit_price, tax_rate: line.tax_rate })),
    };
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      const invoice = await createInvoice(token, buildPayload());
      setInvoices((current) => [invoice, ...current]);
      setSuccess(`Facture ${invoice.invoice_number} créée.`);
      setForm(createEmptyInvoiceForm(clients));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Création de la facture impossible.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="invoices-panel" aria-labelledby="invoices-title">
      <div className="section-heading"><div><p className="eyebrow">Création de factures</p><h2 id="invoices-title">Factures</h2></div><button type="button" className="secondary-button" onClick={refreshInvoices} disabled={isLoading}>Actualiser</button></div>
      {clients.length === 0 ? <p className="info-card">Créez d’abord un client pour pouvoir émettre une facture.</p> : (
        <form className="invoice-form" onSubmit={submit}>
          <h3>Créer une facture</h3>
          <div className="form-grid">
            <label>Client<select value={form.client_id} onChange={(event) => updateField('client_id', event.target.value)} required>{clients.map((client) => <option value={client.id} key={client.id}>{client.name}</option>)}</select></label>
            <label>Numéro manuel (optionnel)<input value={form.invoice_number} onChange={(event) => updateField('invoice_number', event.target.value)} placeholder="Généré automatiquement si vide" /></label>
            <label>Date d’émission<input type="date" value={form.issue_date} onChange={(event) => updateField('issue_date', event.target.value)} required /></label>
            <label>Date d’échéance<input type="date" value={form.due_date} onChange={(event) => updateField('due_date', event.target.value)} /></label>
          </div>
          <div className="invoice-lines">
            <div className="line-header"><h4>Lignes de facture</h4><button type="button" className="secondary-button" onClick={addLine}>Ajouter une ligne</button></div>
            {form.lines.map((line, index) => {
              const calculatedLine = totals.lines[index];
              return (
                <div className="invoice-line" key={index}>
                  <label>Description<input value={line.description} onChange={(event) => updateLine(index, 'description', event.target.value)} required /></label>
                  <label>Quantité<input type="number" min="0.001" step="0.001" value={line.quantity} onChange={(event) => updateLine(index, 'quantity', event.target.value)} required /></label>
                  <label>Prix HT<input type="number" min="0" step="0.01" value={line.unit_price} onChange={(event) => updateLine(index, 'unit_price', event.target.value)} required /></label>
                  <label>TVA %<input type="number" min="0" step="0.1" value={line.tax_rate} onChange={(event) => updateLine(index, 'tax_rate', event.target.value)} required /></label>
                  <div className="line-total"><span>HT {formatAmount(calculatedLine.lineTotalExcludingTax)}</span><span>TVA {formatAmount(calculatedLine.lineTotalTax)}</span><span>TTC {formatAmount(calculatedLine.lineTotalIncludingTax)}</span></div>
                  {form.lines.length > 1 && <button type="button" className="danger-button" onClick={() => removeLine(index)}>Retirer</button>}
                </div>
              );
            })}
          </div>
          <div className="totals-card" aria-live="polite"><span>Total HT <strong>{formatAmount(totals.totalExcludingTax)}</strong></span><span>Total TVA <strong>{formatAmount(totals.totalTax)}</strong></span><span>Total TTC <strong>{formatAmount(totals.totalIncludingTax)}</strong></span></div>
          {error && <p className="error" role="alert">{error}</p>}
          {success && <p className="success" role="status">{success}</p>}
          <div className="form-actions"><button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Création...' : 'Créer la facture'}</button></div>
        </form>
      )}
      <div className="invoices-list">
        {isLoading ? <p>Chargement des factures...</p> : invoices.length === 0 ? <p>Aucune facture créée pour le moment.</p> : invoices.map((invoice) => (
          <article className="invoice-card" key={invoice.id}>
            <div><span className="badge">{invoice.status}</span><h3>{invoice.invoice_number}</h3><p>Émise le {invoice.issue_date}{invoice.due_date ? ` · échéance ${invoice.due_date}` : ''}</p></div>
            <div className="invoice-amounts"><span>HT {formatAmount(invoice.total_excluding_tax)}</span><span>TVA {formatAmount(invoice.total_tax)}</span><strong>TTC {formatAmount(invoice.total_including_tax)}</strong></div>
          </article>
        ))}
      </div>
    </section>
  );
}


createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
