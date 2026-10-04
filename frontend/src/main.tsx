import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { CustomerDemo } from './pages/CustomerDemo'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {window.location.pathname.replace(/\/$/, '') === '/demo/customer' ? <CustomerDemo /> : <App />}
  </StrictMode>,
)
