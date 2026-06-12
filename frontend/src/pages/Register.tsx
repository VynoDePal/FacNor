import React, { useState } from 'react';
import api from '../api/apiClient';
import { useNavigate } from 'react-router-dom';

const Register = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await api.post('/auth/register', { username, email, password });
      navigate('/login');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed');
    }
  };

  return (
    <div style={{ maxWidth: '400px', margin: '0 auto', padding: '20px' }}>
      <h2>Register</h2>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '10px' }}>
          <label>Username:</label><br/>
          <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} style={{ width: '100%' }} />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>Email:</label><br/>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} style={{ width: '100%' }} />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>Password:</label><br/>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} style={{ width: '100%' }} />
        </div>
        {error && <p style={{ color: 'red' }}>{error}</p>}
        <button type="submit">Register</button>
      </form>
    </div>
  );
};

export default Register;
