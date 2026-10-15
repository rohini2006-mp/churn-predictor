import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { useEffect, useState } from 'react'
import { AuthScreen, type AuthUser } from './AuthScreen'
import { api } from './services/api'

function Root() {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [checking, setChecking] = useState(true)
  useEffect(() => {
    if (!localStorage.getItem('churnpilot_access_token')) {
      setChecking(false)
      return
    }
    void api.authMe().then((result) => setUser(result.user)).catch(() => localStorage.removeItem('churnpilot_access_token')).finally(() => setChecking(false))
  }, [])
  if (checking) return <main className="auth-shell"><div className="auth-loading">Loading secure workspace…</div></main>
  if (!user) return <AuthScreen onAuthenticated={setUser} />
  return <App user={user} onLogout={() => { void api.authLogout().finally(() => { localStorage.removeItem('churnpilot_access_token'); setUser(null) }) }} />
}

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><Root /></React.StrictMode>)
