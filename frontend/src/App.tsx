import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import Clients from './pages/Clients';
import Invoices from './pages/Invoices';

const App = () => {
  return (
    <Router>
      <nav style={{ padding: '10px', background: '#eee', display: 'flex', gap: '10px' }}>
        <Link to="/clients">Clients</Link>
        <Link to="/invoices">Invoices</Link>
        <Link to="/login">Login</Link>
        <Link to="/register">Register</Link>
        <button onClick={() => { localStorage.removeItem('token'); window.location.href = '/login'; }}>Logout</button>
      </nav>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/clients" element={<Clients />} />
        <Route path="/invoices" element={<Invoices />} />
        <Route path="/" element={<div style={{ padding: '20px' }}><h1>Welcome to FacNor</h1><p>Please login to manage your invoices.</p></div>} />
      </Routes>
    </Router>
  );
};

export default App;

