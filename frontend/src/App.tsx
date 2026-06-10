import React, { useState } from "react";
import ClientManager from "./components/ClientManager";
import InvoiceForm from "./components/InvoiceForm";
import InvoiceList from "./components/InvoiceList";

function App() {
  const [view, setView] = useState("clients"); // "clients", "invoices", "create_invoice"

  return (
    <div style={{ padding: '20px' }}>
      <h1>FacNor - Gestion de Factures</h1>
      <p>Bienvenue sur l'application de gestion de factures normalisées.</p>
      <hr />
      <div style={{ marginBottom: '20px', display: 'flex', gap: '10px' }}>
        <button 
          onClick={() => setView("clients")}
          style={{ padding: '10px 20px', cursor: 'pointer', backgroundColor: view === "clients" ? "#ddd" : "#fff" }}
        >
          Clients
        </button>
        <button 
          onClick={() => setView("invoices")}
          style={{ padding: '10px 20px', cursor: 'pointer', backgroundColor: view === "invoices" ? "#ddd" : "#fff" }}
        >
          Factures
        </button>
        <button 
          onClick={() => setView("create_invoice")}
          style={{ padding: '10px 20px', cursor: 'pointer', backgroundColor: view === "create_invoice" ? "#ddd" : "#fff" }}
        >
          Nouvelle Facture
        </button>
      </div>
      {view === "clients" && <ClientManager />}
      {view === "invoices" && <InvoiceList />}
      {view === "create_invoice" && <InvoiceForm />}
    </div>
  );
}

export default App;
