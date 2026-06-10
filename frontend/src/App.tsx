import React, { useState } from "react";
import ClientManager from "./components/ClientManager";
import InvoiceForm from "./components/InvoiceForm";

function App() {
  const [showInvoiceForm, setShowInvoiceForm] = useState(false);

  return (
    <div style={{ padding: '20px' }}>
      <h1>FacNor - Gestion de Factures</h1>
      <p>Bienvenue sur l'application de gestion de factures normalisées.</p>
      <hr />
      <div style={{ marginBottom: '20px' }}>
        <button 
          onClick={() => setShowInvoiceForm(!showInvoiceForm)}
          style={{ padding: '10px 20px', cursor: 'pointer' }}
        >
          {showInvoiceForm ? "Hide Invoice Form" : "Create New Invoice"}
        </button>
      </div>
      {showInvoiceForm ? <InvoiceForm /> : <ClientManager />}
    </div>
  );
}

export default App;
