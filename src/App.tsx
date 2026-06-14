import { FormEvent, useEffect, useState } from 'react';
import { AuthResponse, Client, ClientPayload, ClientType, Invoice, InvoiceItemPayload, InvoicePayload, InvoiceStatus, User, createClient, createInvoice, downloadInvoicePdf, fetchClients, fetchHealth, fetchInvoices, getApiBaseUrl, login, updateClient } from './api';
import './styles.css';

type ApiState = 'loading' | 'online' | 'offline';
type View = 'login' | 'dashboard';

type ClientFormState = {
  name: string;
  client_type: ClientType;
  email: string;
  address: string;
  siren: string;
  vat_number: string;
};

type InvoiceFormState = {
  client_id: string;
  issue_date: string;
  due_date: string;
  status: InvoiceStatus;
  items: InvoiceItemPayload[];
};

const TOKEN_STORAGE_KEY = 'facnor_access_token';
const USER_STORAGE_KEY = 'facnor_user';
const emptyClientForm: ClientFormState = { name: '', client_type: 'individual', email: '', address: '', siren: '', vat_number: '' };
const emptyInvoiceItem: InvoiceItemPayload = { description: '', quantity: '1', unit_price_excluding_tax: '0', vat_rate: '20' };

function newInvoiceForm(): InvoiceFormState {
  return { client_id: '', issue_date: new Date().toISOString().slice(0, 10), due_date: '', status: 'draft', items: [{ ...emptyInvoiceItem }] };
}

function readStoredUser(): User | null {
  const rawUser = window.localStorage.getItem(USER_STORAGE_KEY);
  if (!rawUser) return null;
  try {
    return JSON.parse(rawUser) as User;
  } catch {
    window.localStorage.removeItem(USER_STORAGE_KEY);
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    return null;
  }
}

function readStoredToken(): string {
  return window.localStorage.getItem(TOKEN_STORAGE_KEY) || '';
}

function toClientPayload(form: ClientFormState): ClientPayload {
  return {
    name: form.name.trim(),
    client_type: form.client_type,
    email: form.email.trim() || null,
    address: form.address.trim() || null,
    siren: form.client_type === 'company' ? form.siren.trim() || null : null,
    vat_number: form.client_type === 'company' ? form.vat_number.trim() || null : null,
  };
}

function toClientForm(client: Client): ClientFormState {
  return {
    name: client.name,
    client_type: client.client_type,
    email: client.email || '',
    address: client.address || '',
    siren: client.siren || '',
    vat_number: client.vat_number || '',
  };
}

function toInvoicePayload(form: InvoiceFormState): InvoicePayload {
  return {
    client_id: Number(form.client_id),
    issue_date: form.issue_date,
    due_date: form.due_date || null,
    status: form.status,
    items: form.items.map((item) => ({
      description: item.description.trim(),
      quantity: item.quantity,
      unit_price_excluding_tax: item.unit_price_excluding_tax,
      vat_rate: item.vat_rate,
    })),
  };
}

function formatMoney(value: string): string {
  return `${Number(value).toFixed(2)} €`;
}

export function App() {
  const [apiState, setApiState] = useState<ApiState>('loading');
  const [message, setMessage] = useState('Connexion à l’API FacNor…');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentUser, setCurrentUser] = useState<User | null>(() => readStoredUser());
  const [accessToken, setAccessToken] = useState(() => readStoredToken());
  const [view, setView] = useState<View>(() => (window.localStorage.getItem(TOKEN_STORAGE_KEY) ? 'dashboard' : 'login'));
  const [clients, setClients] = useState<Client[]>([]);
  const [clientsError, setClientsError] = useState('');
  const [clientsMessage, setClientsMessage] = useState('');
  const [isLoadingClients, setIsLoadingClients] = useState(false);
  const [isSavingClient, setIsSavingClient] = useState(false);
  const [editingClientId, setEditingClientId] = useState<number | null>(null);
  const [clientForm, setClientForm] = useState<ClientFormState>(emptyClientForm);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [invoicesError, setInvoicesError] = useState('');
  const [invoicesMessage, setInvoicesMessage] = useState('');
  const [isLoadingInvoices, setIsLoadingInvoices] = useState(false);
  const [isSavingInvoice, setIsSavingInvoice] = useState(false);
  const [downloadingInvoiceId, setDownloadingInvoiceId] = useState<number | null>(null);
  const [invoiceForm, setInvoiceForm] = useState<InvoiceFormState>(() => newInvoiceForm());

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

  useEffect(() => {
    if (view !== 'dashboard' || !accessToken) return;
    setIsLoadingClients(true);
    setClientsError('');
    fetchClients(accessToken)
      .then(setClients)
      .catch((error: unknown) => setClientsError(error instanceof Error ? error.message : 'Chargement des clients impossible.'))
      .finally(() => setIsLoadingClients(false));

    setIsLoadingInvoices(true);
    setInvoicesError('');
    fetchInvoices(accessToken)
      .then(setInvoices)
      .catch((error: unknown) => setInvoicesError(error instanceof Error ? error.message : 'Chargement des factures impossible.'))
      .finally(() => setIsLoadingInvoices(false));
  }, [accessToken, view]);

  function storeSession(auth: AuthResponse) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, auth.access_token);
    window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(auth.user));
    setAccessToken(auth.access_token);
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
    setAccessToken('');
    setCurrentUser(null);
    setClients([]);
    setInvoices([]);
    setPassword('');
    setView('login');
  }

  function resetClientForm() {
    setEditingClientId(null);
    setClientForm(emptyClientForm);
  }

  function handleEditClient(client: Client) {
    setEditingClientId(client.id);
    setClientForm(toClientForm(client));
    setClientsMessage('');
    setClientsError('');
  }

  async function handleClientSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSavingClient(true);
    setClientsError('');
    setClientsMessage('');
    try {
      const payload = toClientPayload(clientForm);
      const savedClient = editingClientId ? await updateClient(accessToken, editingClientId, payload) : await createClient(accessToken, payload);
      setClients((currentClients) => editingClientId ? currentClients.map((client) => (client.id === savedClient.id ? savedClient : client)) : [...currentClients, savedClient]);
      setClientsMessage(editingClientId ? 'Client modifié avec succès.' : 'Client créé avec succès.');
      resetClientForm();
    } catch (error: unknown) {
      setClientsError(error instanceof Error ? error.message : 'Enregistrement du client impossible.');
    } finally {
      setIsSavingClient(false);
    }
  }

  function updateInvoiceItem(index: number, field: keyof InvoiceItemPayload, value: string) {
    setInvoiceForm((currentForm) => ({
      ...currentForm,
      items: currentForm.items.map((item, itemIndex) => itemIndex === index ? { ...item, [field]: value } : item),
    }));
  }

  function addInvoiceItem() {
    setInvoiceForm((currentForm) => ({ ...currentForm, items: [...currentForm.items, { ...emptyInvoiceItem }] }));
  }

  function removeInvoiceItem(index: number) {
    setInvoiceForm((currentForm) => ({ ...currentForm, items: currentForm.items.filter((_, itemIndex) => itemIndex !== index) }));
  }

  async function handleInvoiceSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSavingInvoice(true);
    setInvoicesError('');
    setInvoicesMessage('');
    try {
      const savedInvoice = await createInvoice(accessToken, toInvoicePayload(invoiceForm));
      setInvoices((currentInvoices) => [...currentInvoices, savedInvoice]);
      setInvoicesMessage(`Facture ${savedInvoice.invoice_number} créée avec succès.`);
      setInvoiceForm(newInvoiceForm());
    } catch (error: unknown) {
      setInvoicesError(error instanceof Error ? error.message : 'Création de la facture impossible.');
    } finally {
      setIsSavingInvoice(false);
    }
  }

  async function handleDownloadInvoicePdf(invoice: Invoice) {
    setDownloadingInvoiceId(invoice.id);
    setInvoicesError('');
    setInvoicesMessage('');
    try {
      await downloadInvoicePdf(accessToken, invoice);
      setInvoicesMessage(`Téléchargement du PDF ${invoice.invoice_number} lancé.`);
    } catch (error: unknown) {
      setInvoicesError(error instanceof Error ? error.message : 'Téléchargement du PDF impossible.');
    } finally {
      setDownloadingInvoiceId(null);
    }
  }

  function clientName(clientId: number): string {
    return clients.find((client) => client.id === clientId)?.name || `Client #${clientId}`;
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">FacNor</p>
        <h1>Gestion de factures normalisées</h1>
        <p className="lede">Connectez-vous pour accéder au tableau de bord de gestion des factures normalisées.</p>
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
            <label>Email<input autoComplete="email" name="email" onChange={(event) => setEmail(event.target.value)} placeholder="marie@example.com" required type="email" value={email} /></label>
            <label>Mot de passe<input autoComplete="current-password" minLength={8} name="password" onChange={(event) => setPassword(event.target.value)} placeholder="Votre mot de passe" required type="password" value={password} /></label>
            {authError ? <p className="form-error" role="alert">{authError}</p> : null}
            <button disabled={isSubmitting || apiState === 'offline'} type="submit">{isSubmitting ? 'Connexion…' : 'Se connecter'}</button>
          </form>
        </section>
      ) : (
        <>
          <section className="dashboard-card" aria-labelledby="dashboard-title">
            <div>
              <p className="eyebrow">Tableau de bord</p>
              <h2 id="dashboard-title">Bienvenue{currentUser?.full_name ? `, ${currentUser.full_name}` : ''}</h2>
              <p className="muted">Vous êtes connecté avec le compte <strong>{currentUser?.email}</strong>. Vous pouvez maintenant gérer vos clients et factures.</p>
            </div>
            <button className="secondary-button" type="button" onClick={handleLogout}>Se déconnecter</button>
          </section>

          <section className="clients-card" aria-labelledby="clients-title">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Clients</p>
                <h2 id="clients-title">Gestion des clients</h2>
                <p className="muted">Créez, modifiez et consultez les clients utilisés dans vos factures.</p>
              </div>
              <span className="client-count">{clients.length} client{clients.length > 1 ? 's' : ''}</span>
            </div>

            <form className="client-form" onSubmit={handleClientSubmit}>
              <label>Nom du client<input name="client-name" onChange={(event) => setClientForm({ ...clientForm, name: event.target.value })} placeholder="Dupont SAS" required value={clientForm.name} /></label>
              <label>Type<select name="client-type" onChange={(event) => setClientForm({ ...clientForm, client_type: event.target.value as ClientType })} value={clientForm.client_type}><option value="individual">Particulier</option><option value="company">Entreprise</option></select></label>
              <label>Email<input name="client-email" onChange={(event) => setClientForm({ ...clientForm, email: event.target.value })} placeholder="contact@example.com" type="email" value={clientForm.email} /></label>
              <label>Adresse<textarea name="client-address" onChange={(event) => setClientForm({ ...clientForm, address: event.target.value })} placeholder="1 rue de Paris, 75001 Paris" rows={3} value={clientForm.address} /></label>
              {clientForm.client_type === 'company' ? <><label>SIREN<input inputMode="numeric" name="client-siren" onChange={(event) => setClientForm({ ...clientForm, siren: event.target.value })} placeholder="732 829 320" required value={clientForm.siren} /></label><label>Numéro de TVA<input name="client-vat" onChange={(event) => setClientForm({ ...clientForm, vat_number: event.target.value })} placeholder="FR 44 732829320" required value={clientForm.vat_number} /></label></> : null}
              {clientsError ? <p className="form-error" role="alert">{clientsError}</p> : null}
              {clientsMessage ? <p className="form-success">{clientsMessage}</p> : null}
              <div className="form-actions">
                <button disabled={isSavingClient || !accessToken} type="submit">{isSavingClient ? 'Enregistrement…' : editingClientId ? 'Modifier le client' : 'Créer le client'}</button>
                {editingClientId ? <button className="secondary-button" type="button" onClick={resetClientForm}>Annuler</button> : null}
              </div>
            </form>

            <div className="clients-list" aria-live="polite">
              <h3>Liste des clients</h3>
              {isLoadingClients ? <p className="muted">Chargement des clients…</p> : null}
              {!isLoadingClients && clients.length === 0 ? <p className="muted">Aucun client enregistré.</p> : null}
              {clients.map((client) => (
                <article className="client-item" key={client.id}>
                  <div>
                    <h4>{client.name}</h4>
                    <p className="muted">{client.client_type === 'company' ? 'Entreprise' : 'Particulier'}{client.email ? ` · ${client.email}` : ''}</p>
                    {client.address ? <p>{client.address}</p> : null}
                    {client.siren ? <small>SIREN {client.siren} · TVA {client.vat_number}</small> : null}
                  </div>
                  <button className="secondary-button" type="button" onClick={() => handleEditClient(client)}>Modifier</button>
                </article>
              ))}
            </div>
          </section>

          <section className="invoices-card" aria-labelledby="invoices-title">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Factures</p>
                <h2 id="invoices-title">Gestion des factures</h2>
                <p className="muted">Créez une facture avec plusieurs lignes de produits et consultez la liste.</p>
              </div>
              <span className="client-count">{invoices.length} facture{invoices.length > 1 ? 's' : ''}</span>
            </div>

            <form className="invoice-form" onSubmit={handleInvoiceSubmit}>
              <label>Client<select name="invoice-client" onChange={(event) => setInvoiceForm({ ...invoiceForm, client_id: event.target.value })} required value={invoiceForm.client_id}><option value="">Choisir un client</option>{clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}</select></label>
              <label>Date d’émission<input name="invoice-issue-date" onChange={(event) => setInvoiceForm({ ...invoiceForm, issue_date: event.target.value })} required type="date" value={invoiceForm.issue_date} /></label>
              <label>Date d’échéance<input name="invoice-due-date" onChange={(event) => setInvoiceForm({ ...invoiceForm, due_date: event.target.value })} type="date" value={invoiceForm.due_date} /></label>
              <label>Statut<select name="invoice-status" onChange={(event) => setInvoiceForm({ ...invoiceForm, status: event.target.value as InvoiceStatus })} value={invoiceForm.status}><option value="draft">Brouillon</option><option value="issued">Émise</option><option value="paid">Payée</option><option value="cancelled">Annulée</option></select></label>

              <div className="invoice-lines">
                <h3>Lignes de produits</h3>
                {invoiceForm.items.map((item, index) => (
                  <div className="invoice-line" key={index}>
                    <label>Description<input name={`invoice-line-description-${index}`} onChange={(event) => updateInvoiceItem(index, 'description', event.target.value)} placeholder="Prestation de service" required value={item.description} /></label>
                    <label>Quantité<input min="0.01" name={`invoice-line-quantity-${index}`} onChange={(event) => updateInvoiceItem(index, 'quantity', event.target.value)} required step="0.01" type="number" value={item.quantity} /></label>
                    <label>Prix HT<input min="0" name={`invoice-line-unit-price-${index}`} onChange={(event) => updateInvoiceItem(index, 'unit_price_excluding_tax', event.target.value)} required step="0.01" type="number" value={item.unit_price_excluding_tax} /></label>
                    <label>TVA %<input min="0" name={`invoice-line-vat-${index}`} onChange={(event) => updateInvoiceItem(index, 'vat_rate', event.target.value)} required step="0.1" type="number" value={item.vat_rate} /></label>
                    {invoiceForm.items.length > 1 ? <button className="secondary-button" type="button" onClick={() => removeInvoiceItem(index)}>Retirer</button> : null}
                  </div>
                ))}
                <button className="secondary-button" type="button" onClick={addInvoiceItem}>Ajouter une ligne</button>
              </div>

              {invoicesError ? <p className="form-error" role="alert">{invoicesError}</p> : null}
              {invoicesMessage ? <p className="form-success">{invoicesMessage}</p> : null}
              <button disabled={isSavingInvoice || !accessToken || clients.length === 0} type="submit">{isSavingInvoice ? 'Création…' : 'Créer la facture'}</button>
            </form>

            <div className="invoices-list" aria-live="polite">
              <h3>Liste des factures</h3>
              {isLoadingInvoices ? <p className="muted">Chargement des factures…</p> : null}
              {!isLoadingInvoices && invoices.length === 0 ? <p className="muted">Aucune facture enregistrée.</p> : null}
              {invoices.map((invoice) => (
                <article className="invoice-item" key={invoice.id}>
                  <div>
                    <h4>{invoice.invoice_number} · {clientName(invoice.client_id)}</h4>
                    <p className="muted">{invoice.issue_date}{invoice.due_date ? ` · Échéance ${invoice.due_date}` : ''} · {invoice.status}</p>
                    <p><strong>Total TTC : {formatMoney(invoice.total_including_tax)}</strong> · HT {formatMoney(invoice.total_excluding_tax)} · TVA {formatMoney(invoice.total_vat)}</p>
                    <ul>{invoice.items.map((item) => <li key={item.id}>{item.description} — {item.quantity} × {formatMoney(item.unit_price_excluding_tax)} HT, TVA {item.vat_rate}%</li>)}</ul>
                  </div>
                  <button className="secondary-button" disabled={downloadingInvoiceId === invoice.id || !accessToken} type="button" onClick={() => handleDownloadInvoicePdf(invoice)}>
                    {downloadingInvoiceId === invoice.id ? 'Téléchargement…' : 'Télécharger le PDF'}
                  </button>
                </article>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
