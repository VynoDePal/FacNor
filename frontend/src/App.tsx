import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useParams } from 'react-router-dom';
import ClientList from './pages/ClientList';
import ClientForm from './pages/ClientForm';
import InvoiceList from './pages/InvoiceList';
import InvoiceForm from './pages/InvoiceForm';
import './App.css';

const ClientFormWrapper = () => {
  const { id } = useParams();
  return <ClientForm clientId={id} />;
};

function App() {
  return (
    <Router>
      <nav style={{ padding: '10px', background: '#eee', marginBottom: '20px' }}>
        <Link to="/clients" style={{ marginRight: '20px' }}>Clients</Link>
        <Link to="/factures">Factures</Link>
      </nav>
      <div style={{ padding: '0 20px' }}>
        <Routes>
          <Route path="/clients" element={<ClientList />} />
          <Route path="/clients/new" element={<ClientForm />} />
          <Route path="/clients/edit/:id" element={<ClientFormWrapper />} />
          <Route path="/factures" element={<InvoiceList />} />
          <Route path="/factures/new" element={<InvoiceForm />} />
          <Route path="/factures/edit/:id" element={<InvoiceForm />} />
          <Route path="/" element={<ClientList />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
