import { FormEvent, useEffect, useMemo, useState } from 'react';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
const storedToken = 'facnor.authToken';

type ApiStatus = 'idle' | 'loading' | 'ready' | 'error';
type ClientType = 'B2B' | 'B2C';
type InvoiceStatus = 'draft' | 'issued' | 'paid' | 'cancelled';

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

type InvoiceLine = {
  id: number;
  line_order: number;
  description: string;
  quantity: string;
  unit_price_excluding_tax: string;
  vat_rate: string;
  line_total_excluding_tax: string;
  line_total_tax: string;
  line_total_including_tax: string;
};

type Invoice = {
  id: number;
  user_id: number;
  client_id: number;
  invoice_number: string;
  issue_date: string;
  due_date: string | null;
  status: InvoiceStatus;
  currency: string;
  total_excluding_tax: string;
  total_tax: string;
  total_including_tax: string;
  legal_notice: string | null;
  lines: InvoiceLine[];
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

type InvoiceLineForm = {
  description: string;
  quantity: string;
  unit_price_excluding_tax: string;
  vat_rate: string;
};

type InvoiceForm = {
  client_id: string;
  issue_date: string;
  due_date: string;
  currency: string;
  legal_notice: string;
  lines: InvoiceLineForm[];
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

const defaultLegalNotice = 'Pénalités de retard exigibles et indemnité forfaitaire de recouvrement de 40 €.';

const emptyInvoiceLine = (): InvoiceLineForm => ({
  description: '',
  quantity: '1',
  unit_price_excluding_tax: '0',
  vat_rate: '20',
});

const emptyInvoiceForm = (): InvoiceForm => ({
  client_id: '',
  issue_date: new Date().toISOString().slice(0, 10),
  due_date: '',
  currency: 'EUR',
  legal_notice: defaultLegalNotice,
  lines: [emptyInvoiceLine()],
});

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

function parseAmount(value: string) {
  const normalized = Number.parseFloat(value.replace(',', '.'));
  return Number.isFinite(normalized) ? normalized : 0;
}

function roundMoney(value: number) {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function formatMoney(value: number, currency = 'EUR') {
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function invoicePayload(form: InvoiceForm) {
  return {
    client_id: Number(form.client_id),
    issue_date: form.issue_date,
    due_date: optionalText(form.due_date),
    currency: form.currency.trim().toUpperCase(),
    legal_notice: optionalText(form.legal_notice),
    lines: form.lines.map((line) => ({
      description: line.description.trim(),
      quantity: line.quantity,
      unit_price_excluding_tax: line.unit_price_excluding_tax,
      vat_rate: line.vat_rate,
    })),
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
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [clientForm, setClientForm] = useState<ClientForm>(emptyClientForm);
  const [invoiceForm, setInvoiceForm] = useState<InvoiceForm>(emptyInvoiceForm);
  const [clientStatus, setClientStatus] = useState('Connectez-vous pour charger vos clients.');
  const [invoiceStatus, setInvoiceStatus] = useState('Connectez-vous pour gérer vos factures.');
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
    if (response.status === 204) {
      return undefined as T;
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
      setInvoiceForm((current) => ({
        ...current,
        client_id: current.client_id || payload[0]?.id?.toString() || '',
      }));
      setClientStatus(payload.length === 0 ? 'Aucun client enregistré.' : `${payload.length} client(s) chargé(s).`);
    } catch (error) {
      setClientStatus(error instanceof Error ? error.message : 'Impossible de charger les clients.');
    }
  }

  async function loadInvoices() {
    if (!token) {
      return;
    }
    setInvoiceStatus('Chargement des factures…');
    try {
      const payload = await apiRequest<Invoice[]>('/invoices');
      setInvoices(payload);
      setInvoiceStatus(payload.length === 0 ? 'Aucune facture enregistrée.' : `${payload.length} facture(s) chargée(s).`);
    } catch (error) {
      setInvoiceStatus(error instanceof Error ? error.message : 'Impossible de charger les factures.');
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
    loadInvoices();
  }, [token]);

  const invoicePreview = useMemo(() => {
    const lines = invoiceForm.lines.map((line, index) => {
      const quantity = parseAmount(line.quantity);
      const unitPrice = parseAmount(line.unit_price_excluding_tax);
      const vatRate = parseAmount(line.vat_rate);
      const excludingTax = roundMoney(quantity * unitPrice);
      const tax = roundMoney((excludingTax * vatRate) / 100);
      const includingTax = roundMoney(excludingTax + tax);
      return {
        id: index,
        description: line.description,
        excludingTax,
        tax,
        includingTax,
      };
    });

    return {
      lines,
      totalExcludingTax: roundMoney(lines.reduce((sum, line) => sum + line.excludingTax, 0)),
      totalTax: roundMoney(lines.reduce((sum, line) => sum + line.tax, 0)),
      totalIncludingTax: roundMoney(lines.reduce((sum, line) => sum + line.includingTax, 0)),
    };
  }, [invoiceForm.lines]);

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
      setInvoiceStatus('Authentification réussie.');
    } catch (error) {
      const fallback = error instanceof Error ? error.message : 'Authentification impossible.';
      setClientStatus(fallback);
      setInvoiceStatus(fallback);
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
      setInvoiceForm((current) => ({ ...current, client_id: created.id.toString() }));
      setClientForm({ ...emptyClientForm, client_type: clientForm.client_type });
      setClientStatus(`Client « ${created.name} » créé.`);
    } catch (error) {
      setClientStatus(error instanceof Error ? error.message : 'Création du client impossible.');
    }
  }

  async function submitInvoice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setInvoiceStatus('Création de la facture…');
    try {
      const created = await apiRequest<Invoice>('/invoices', {
        method: 'POST',
        body: JSON.stringify(invoicePayload(invoiceForm)),
      });
      setInvoices((current) => [created, ...current.filter((invoice) => invoice.id !== created.id)]);
      setInvoiceForm((current) => ({
        ...emptyInvoiceForm(),
        client_id: current.client_id,
      }));
      setInvoiceStatus(`Facture ${created.invoice_number} créée.`);
    } catch (error) {
      setInvoiceStatus(error instanceof Error ? error.message : 'Création de la facture impossible.');
    }
  }

  async function updateInvoiceStatus(invoiceId: number, nextStatus: InvoiceStatus) {
    setInvoiceStatus('Mise à jour de la facture…');
    try {
      const updated = await apiRequest<Invoice>(`/invoices/${invoiceId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: nextStatus }),
      });
      setInvoices((current) => current.map((invoice) => (invoice.id === invoiceId ? updated : invoice)));
      setInvoiceStatus(`Facture ${updated.invoice_number} mise à jour.`);
    } catch (error) {
      setInvoiceStatus(error instanceof Error ? error.message : 'Mise à jour impossible.');
    }
  }

  async function deleteInvoice(invoiceId: number) {
    setInvoiceStatus('Suppression de la facture…');
    try {
      await apiRequest<void>(`/invoices/${invoiceId}`, { method: 'DELETE' });
      setInvoices((current) => current.filter((invoice) => invoice.id !== invoiceId));
      setInvoiceStatus('Facture supprimée.');
    } catch (error) {
      setInvoiceStatus(error instanceof Error ? error.message : 'Suppression impossible.');
    }
  }

  function updateInvoiceLine(index: number, field: keyof InvoiceLineForm, value: string) {
    setInvoiceForm((current) => ({
      ...current,
      lines: current.lines.map((line, lineIndex) => (lineIndex === index ? { ...line, [field]: value } : line)),
    }));
  }

  function addInvoiceLine() {
    setInvoiceForm((current) => ({ ...current, lines: [...current.lines, emptyInvoiceLine()] }));
  }

  function removeInvoiceLine(index: number) {
    setInvoiceForm((current) => ({
      ...current,
      lines: current.lines.length === 1 ? current.lines : current.lines.filter((_, lineIndex) => lineIndex !== index),
    }));
  }

  function logout() {
    localStorage.removeItem(storedToken);
    setToken('');
    setClients([]);
    setInvoices([]);
    setClientStatus('Connectez-vous pour charger vos clients.');
    setInvoiceStatus('Connectez-vous pour gérer vos factures.');
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

      <section className="panel" aria-labelledby="invoices-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Gestion des factures</p>
            <h2 id="invoices-title">Factures</h2>
          </div>
          <button type="button" onClick={loadInvoices} disabled={!isAuthenticated}>
            Actualiser les factures
          </button>
        </div>
        <p className="status-line">{invoiceStatus}</p>

        <form className="invoice-form" onSubmit={submitInvoice}>
          <label>
            Client facturé
            <select
              value={invoiceForm.client_id}
              onChange={(event) => setInvoiceForm({ ...invoiceForm, client_id: event.target.value })}
              disabled={!isAuthenticated || clients.length === 0}
              required
            >
              <option value="">Sélectionner un client</option>
              {clients.map((client) => (
                <option key={client.id} value={client.id}>
                  {client.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Date d’émission
            <input
              type="date"
              value={invoiceForm.issue_date}
              onChange={(event) => setInvoiceForm({ ...invoiceForm, issue_date: event.target.value })}
              disabled={!isAuthenticated}
              required
            />
          </label>
          <label>
            Date d’échéance
            <input
              type="date"
              value={invoiceForm.due_date}
              onChange={(event) => setInvoiceForm({ ...invoiceForm, due_date: event.target.value })}
              disabled={!isAuthenticated}
            />
          </label>
          <label>
            Devise
            <input
              value={invoiceForm.currency}
              maxLength={3}
              onChange={(event) => setInvoiceForm({ ...invoiceForm, currency: event.target.value.toUpperCase() })}
              disabled={!isAuthenticated}
              required
            />
          </label>
          <label className="wide">
            Mentions légales
            <input
              value={invoiceForm.legal_notice}
              onChange={(event) => setInvoiceForm({ ...invoiceForm, legal_notice: event.target.value })}
              disabled={!isAuthenticated}
            />
          </label>

          <div className="wide invoice-lines-block">
            <div className="invoice-lines-header">
              <h3>Lignes de produits</h3>
              <button type="button" onClick={addInvoiceLine} disabled={!isAuthenticated}>
                Ajouter une ligne
              </button>
            </div>
            <div className="invoice-lines-list">
              {invoiceForm.lines.map((line, index) => (
                <div className="invoice-line-card" key={`${index}-${line.description}`}>
                  <label className="wide">
                    Description
                    <input
                      value={line.description}
                      onChange={(event) => updateInvoiceLine(index, 'description', event.target.value)}
                      disabled={!isAuthenticated}
                      required
                    />
                  </label>
                  <label>
                    Quantité
                    <input
                      type="number"
                      min="0.01"
                      step="0.01"
                      value={line.quantity}
                      onChange={(event) => updateInvoiceLine(index, 'quantity', event.target.value)}
                      disabled={!isAuthenticated}
                      required
                    />
                  </label>
                  <label>
                    Prix unitaire HT
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={line.unit_price_excluding_tax}
                      onChange={(event) => updateInvoiceLine(index, 'unit_price_excluding_tax', event.target.value)}
                      disabled={!isAuthenticated}
                      required
                    />
                  </label>
                  <label>
                    TVA (%)
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={line.vat_rate}
                      onChange={(event) => updateInvoiceLine(index, 'vat_rate', event.target.value)}
                      disabled={!isAuthenticated}
                      required
                    />
                  </label>
                  <div className="line-summary">
                    <strong>Total TTC :</strong>{' '}
                    {formatMoney(invoicePreview.lines[index]?.includingTax ?? 0, invoiceForm.currency || 'EUR')}
                  </div>
                  <button type="button" onClick={() => removeInvoiceLine(index)} disabled={!isAuthenticated || invoiceForm.lines.length === 1}>
                    Supprimer la ligne
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="wide totals-grid">
            <article className="total-card">
              <span>Total HT</span>
              <strong>{formatMoney(invoicePreview.totalExcludingTax, invoiceForm.currency || 'EUR')}</strong>
            </article>
            <article className="total-card">
              <span>Total TVA</span>
              <strong>{formatMoney(invoicePreview.totalTax, invoiceForm.currency || 'EUR')}</strong>
            </article>
            <article className="total-card total-highlight">
              <span>Montant TTC</span>
              <strong>{formatMoney(invoicePreview.totalIncludingTax, invoiceForm.currency || 'EUR')}</strong>
            </article>
          </div>

          <button type="submit" disabled={!isAuthenticated || clients.length === 0 || !invoiceForm.client_id}>
            Créer la facture
          </button>
        </form>

        <div className="invoice-list" aria-live="polite">
          {invoices.map((invoice) => {
            const client = clients.find((item) => item.id === invoice.client_id);
            return (
              <article className="invoice-card" key={invoice.id}>
                <div className="invoice-card-header">
                  <div>
                    <strong>{invoice.invoice_number}</strong>
                    <p>{client?.name ?? `Client #${invoice.client_id}`}</p>
                  </div>
                  <span className={`status-badge status-${invoice.status}`}>{invoice.status}</span>
                </div>
                <dl className="invoice-meta">
                  <div>
                    <dt>Date</dt>
                    <dd>{invoice.issue_date}</dd>
                  </div>
                  <div>
                    <dt>Échéance</dt>
                    <dd>{invoice.due_date ?? '—'}</dd>
                  </div>
                  <div>
                    <dt>Total TTC</dt>
                    <dd>{formatMoney(parseAmount(invoice.total_including_tax), invoice.currency)}</dd>
                  </div>
                </dl>
                <div className="invoice-lines-readonly">
                  {invoice.lines.map((line) => (
                    <p key={line.id}>
                      {line.description} · {line.quantity} × {line.unit_price_excluding_tax} HT · TVA {line.vat_rate}%
                    </p>
                  ))}
                </div>
                <div className="invoice-actions">
                  {invoice.status === 'draft' && (
                    <button type="button" onClick={() => updateInvoiceStatus(invoice.id, 'issued')}>
                      Marquer émise
                    </button>
                  )}
                  {invoice.status !== 'paid' && (
                    <button type="button" onClick={() => updateInvoiceStatus(invoice.id, 'paid')}>
                      Marquer payée
                    </button>
                  )}
                  <button type="button" onClick={() => deleteInvoice(invoice.id)}>
                    Supprimer
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </main>
  );
}
