/**
 * main.tsx — React application entry point.
 *
 * Renders the root <App /> component into the #root div (defined in index.html).
 * StrictMode enables extra warnings during development (e.g., detecting side effects).
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'     // Global styles (Tailwind CSS base + custom)
import App from './App.tsx'

// Mount the React app to the DOM — this is the single entry point for the entire UI
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
