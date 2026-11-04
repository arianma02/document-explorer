import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

const basePath = import.meta.env.BASE_URL
const path = window.location.pathname
const isWorkspace =
  path === basePath || path === basePath.replace(/\/$/, '') || path === `${basePath}index.html`

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {isWorkspace ? (
      <App />
    ) : (
      <main className="not-found">
        <h1>Page not found</h1>
        <p>This address does not belong to a page in Document Explorer.</p>
        <a href={basePath}>Open the workspace</a>
      </main>
    )}
  </StrictMode>,
)
