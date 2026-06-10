import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [message, setMessage] = useState('Loading...')
  const [status, setStatus] = useState('')

  useEffect(() => {
    fetch('http://localhost:8000/')
      .then(res => res.json())
      .then(data => {
        setMessage(data.message)
        setStatus(data.status)
      })
      .catch(err => {
        console.error('Error fetching data:', err)
        setMessage('Error connecting to backend')
        setStatus('error')
      })
  }, [])

  return (
    <div className="App">
      <h1>FacNor - Gestion de Factures</h1>
      <div className="card">
        <p>Backend Message: <strong>{message}</strong></p>
        <p>Backend Status: <strong>{status}</strong></p>
      </div>
      <p className="read-the-docs">
        Frontend initialized with React + TypeScript + Vite.
      </p>
    </div>
  )
}

export default App
