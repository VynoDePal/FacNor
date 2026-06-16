import { FormEvent, useEffect, useMemo, useState } from 'react';
import { AuthUser, Client, ClientPayload, Invoice, createClient, createInvoice, fetchClients, fetchCurrentUser, fetchInvoices, login } from './api';
import './styles.css';

const TOKEN_KEY = 'facnor_access_token';
const emptyClient: ClientPayload = { name: '', email: '', address: '', postal_code: '', city: '', country: 'France', siren: '', vat_number: '' };
const emptyLine = { description: '', quantity: '1', unitPrice: '', vatRate: '20' };
type LineForm = typeof emptyLine;

const cents = (value: string) => Math.round((Number.parseFloat(value.replace(',', '.')) || 0) * 100);
const money = (value: number) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(value / 100);
function lineTotal(line: LineForm) {
  const ht = Math.round((Number.parseFloat(line.quantity.replace(',', '.')) || 0) * cents(line.unitPrice));
  const tva = Math.round((ht * (Number.parseFloat(line.vatRate.replace(',', '.')) || 0)) / 100);
  return { ht, tva, ttc: ht + tva };
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [user, setUser] = useState<AuthUser | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [tab, setTab] = useState<'invoices' | 'clients'>('invoices');
  const [clientForm, setClientForm] = useState<ClientPayload>(emptyClient);
  const [invoiceClientId, setInvoiceClientId] = useState('');
  const [issueDate, setIssueDate] = useState(new Date().toISOString().slice(0, 10));
  const [dueDate, setDueDate] = useState('');
  const [lines, setLines] = useState<LineForm[]>([{ ...emptyLine }]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [busy, setBusy] = useState(false);

  const totals = useMemo(() => lines.reduce((sum, line) => {
    const current = lineTotal(line);
    return { ht: sum.ht + current.ht, tva: sum.tva + current.tva, ttc: sum.ttc + current.ttc };
  }, { ht: 0, tva: 0, ttc: 0 }), [lines]);

  useEffect(() => {
    if (!token) { setUser(null); setClients([]); setInvoices([]); return; }
    fetchCurrentUser(token).then(setUser).catch(() => { localStorage.removeItem(TOKEN_KEY); setToken(null); });
  }, [token]);

  useEffect(() => {
    if (!token || !user) return;
    Promise.all([fetchClients(token), fetchInvoices(token)]).then(([loadedClients, loadedInvoices]) => {
      setClients(loadedClients);
      setInvoices(loadedInvoices);
      setInvoiceClientId((current) => current || (loadedClients[0] ? String(loadedClients[0].id) : ''));
    }).catch((caught) => setError(caught instanceof Error ? caught.message : 'Chargement impossible'));
  }, [token, user]);

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(''); setSuccess('');
    try {
      const auth = await login(email, password);
      localStorage.setItem(TOKEN_KEY, auth.access_token);
      setToken(auth.access_token); setUser(auth.user);
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Connexion impossible'); }
    finally { setBusy(false); }
  }

  async function submitClient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!token) return;
    setBusy(true); setError(''); setSuccess('');
    try {
      const saved = await createClient(token, {
        ...clientForm,
        name: clientForm.name.trim(), email: clientForm.email?.trim() || null,
        address: clientForm.address.trim(), postal_code: clientForm.postal_code.trim(), city: clientForm.city.trim(),
        country: clientForm.country.trim() || 'France', siren: clientForm.siren?.trim() || null, vat_number: clientForm.vat_number?.trim() || null,
      });
      setClients((current) => [...current, saved]);
      setInvoiceClientId(String(saved.id)); setClientForm(emptyClient); setSuccess('Client ajouté.'); setTab('invoices');
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Création du client impossible'); }
    finally { setBusy(false); }
  }

  async function submitInvoice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!token) return;
    setBusy(true); setError(''); setSuccess('');
    try {
      const invoice = await createInvoice(token, {
        client_id: Number(invoiceClientId), issue_date: issueDate || null, due_date: dueDate || null,
        lines: lines.map((line) => ({ description: line.description.trim(), quantity: Number.parseFloat(line.quantity.replace(',', '.')), unit_price_excluding_tax: cents(line.unitPrice), vat_rate: Number.parseFloat(line.vatRate.replace(',', '.')) })),
      });
      setInvoices((current) => [invoice, ...current]); setLines([{ ...emptyLine }]); setSuccess(`Facture ${invoice.invoice_number} créée.`);
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Création de la facture impossible'); }
    finally { setBusy(false); }
  }

  if (!token || !user) return <main className="page-shell"><section className="hero"><p className="eyebrow">FacNor</p><h1>Gestion de factures normalisées</h1><p>Connectez-vous pour accéder à votre tableau de bord.</p></section><form className="card login-form" onSubmit={submitLogin}><h2>Connexion</h2><label>Adresse e-mail<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label><label>Mot de passe<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>{error && <p className="error">{error}</p>}<button disabled={busy}>{busy ? 'Connexion…' : 'Se connecter'}</button></form></main>;

  return <main className="page-shell dashboard"><section className="card dashboard-header"><div><p className="eyebrow">Tableau de bord</p><h1>Bienvenue, {user.full_name}</h1><p className="muted">Créez vos factures et gérez vos clients.</p></div><button className="secondary" onClick={() => { localStorage.removeItem(TOKEN_KEY); setToken(null); }}>Se déconnecter</button></section><nav className="tabs"><button className={tab === 'invoices' ? 'active' : ''} onClick={() => setTab('invoices')}>Créer une facture</button><button className={tab === 'clients' ? 'active' : ''} onClick={() => setTab('clients')}>Clients</button></nav>{tab === 'invoices' ? <section className="invoice-layout"><form className="card invoice-form" onSubmit={submitInvoice}><div className="section-title"><div><p className="eyebrow">Facturation</p><h2>Nouvelle facture</h2></div><button className="secondary" type="button" onClick={() => setTab('clients')}>Ajouter un client</button></div>{clients.length === 0 ? <p className="muted">Ajoutez d'abord un client.</p> : <><div className="form-grid"><label>Client<select value={invoiceClientId} onChange={(event) => setInvoiceClientId(event.target.value)}>{clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}</select></label><label>Date d'émission<input type="date" value={issueDate} onChange={(event) => setIssueDate(event.target.value)} /></label><label>Date d'échéance<input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} /></label></div><div className="invoice-lines"><div className="line-header"><span>Description</span><span>Qté</span><span>Prix HT</span><span>TVA %</span><span>Total TTC</span><span /></div>{lines.map((line, index) => <div className="invoice-line" key={index}><input value={line.description} onChange={(event) => setLines((current) => current.map((item, i) => i === index ? { ...item, description: event.target.value } : item))} placeholder="Prestation" required /><input type="number" step="0.01" min="0.01" value={line.quantity} onChange={(event) => setLines((current) => current.map((item, i) => i === index ? { ...item, quantity: event.target.value } : item))} required /><input type="number" step="0.01" min="0" value={line.unitPrice} onChange={(event) => setLines((current) => current.map((item, i) => i === index ? { ...item, unitPrice: event.target.value } : item))} required /><input type="number" step="0.1" min="0" value={line.vatRate} onChange={(event) => setLines((current) => current.map((item, i) => i === index ? { ...item, vatRate: event.target.value } : item))} required /><strong>{money(lineTotal(line).ttc)}</strong><button className="ghost" type="button" disabled={lines.length === 1} onClick={() => setLines((current) => current.filter((_, i) => i !== index))}>Retirer</button></div>)}<button className="secondary add-line" type="button" onClick={() => setLines((current) => [...current, { ...emptyLine }])}>Ajouter une ligne</button></div><aside className="totals-card"><div><span>Total HT</span><strong>{money(totals.ht)}</strong></div><div><span>TVA</span><strong>{money(totals.tva)}</strong></div><div className="grand-total"><span>Total TTC</span><strong>{money(totals.ttc)}</strong></div></aside></>}{error && <p className="error">{error}</p>}{success && <p className="success">{success}</p>}<button disabled={busy || clients.length === 0}>{busy ? 'Création…' : 'Créer la facture'}</button></form><aside className="card invoices-list"><p className="eyebrow">Historique</p><h2>{invoices.length} facture{invoices.length > 1 ? 's' : ''}</h2><ul>{invoices.map((invoice) => <li key={invoice.id}><strong>{invoice.invoice_number}</strong><span>{invoice.issue_date}</span><b>{money(invoice.total_including_tax)}</b></li>)}</ul></aside></section> : <section className="clients-layout"><aside className="card clients-list"><div className="section-title"><div><p className="eyebrow">Portefeuille</p><h2>{clients.length} client{clients.length > 1 ? 's' : ''}</h2></div></div><ul>{clients.map((client) => <li key={client.id}><button className="client-row"><strong>{client.name}</strong><span>{client.postal_code} {client.city}</span></button></li>)}</ul></aside><form className="card client-form" onSubmit={submitClient}><p className="eyebrow">Création</p><h2>Nouveau client</h2><div className="form-grid"><label>Nom<input value={clientForm.name} onChange={(event) => setClientForm((current) => ({ ...current, name: event.target.value }))} required /></label><label>E-mail<input type="email" value={clientForm.email ?? ''} onChange={(event) => setClientForm((current) => ({ ...current, email: event.target.value }))} /></label><label className="full-width">Adresse<input value={clientForm.address} onChange={(event) => setClientForm((current) => ({ ...current, address: event.target.value }))} required /></label><label>Code postal<input value={clientForm.postal_code} onChange={(event) => setClientForm((current) => ({ ...current, postal_code: event.target.value }))} required /></label><label>Ville<input value={clientForm.city} onChange={(event) => setClientForm((current) => ({ ...current, city: event.target.value }))} required /></label><label>Pays<input value={clientForm.country} onChange={(event) => setClientForm((current) => ({ ...current, country: event.target.value }))} required /></label><label>SIREN<input value={clientForm.siren ?? ''} onChange={(event) => setClientForm((current) => ({ ...current, siren: event.target.value }))} /></label><label>TVA<input value={clientForm.vat_number ?? ''} onChange={(event) => setClientForm((current) => ({ ...current, vat_number: event.target.value.toUpperCase() }))} /></label></div>{error && <p className="error">{error}</p>}{success && <p className="success">{success}</p>}<button disabled={busy}>{busy ? 'Enregistrement…' : 'Ajouter le client'}</button></form></section>}</main>;
}

export default App;
