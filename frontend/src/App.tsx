import React from "react";
import ClientManager from "./components/ClientManager";

function App() {
  return (
    <div style={{ padding: '20px' }}>
      <h1>FacNor - Gestion de Factures</h1>
      <p>Bienvenue sur l'application de gestion de factures normalisées.</p>
      <hr />
      <ClientManager />
    </div>
  );
}

export default App;
