import { useState, type FormEvent } from 'react'
import { api } from './services/api'

export type AuthUser = { id: string; email: string; display_name: string }

export function AuthScreen({ onAuthenticated }: { onAuthenticated: (user: AuthUser) => void }) {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result = mode === 'login'
        ? await api.authLogin(email, password)
        : await api.authSignup(email, password, displayName)
      localStorage.setItem('churnpilot_access_token', result.access_token)
      onAuthenticated(result.user)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Authentication failed')
    } finally {
      setBusy(false)
    }
  }

  return <main className="auth-shell"><section className="auth-card">
    <div className="brand auth-brand"><div className="brand-mark">C</div><div><strong>ChurnPilot</strong><span>Customer intelligence workspace</span></div></div>
    <span className="panel-eyebrow">{mode === 'login' ? 'WELCOME BACK' : 'GET STARTED'}</span>
    <h1>{mode === 'login' ? 'Sign in to your workspace' : 'Create your account'}</h1>
    <p className="auth-description">Analyze churn risk, train models, and prioritize customer retention from one workspace.</p>
    {error && <div className="auth-error">{error}</div>}
    <form className="auth-form" onSubmit={submit}>
      {mode === 'signup' && <label>Display name<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} required /></label>}
      <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" /></label>
      <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} /></label>
      <button className="button button-primary auth-submit" disabled={busy}>{busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}</button>
    </form>
    <div className="auth-links"><button onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError('') }}>{mode === 'login' ? 'Create an account' : 'Back to sign in'}</button></div>
    <p className="auth-footnote">Local development authentication is enabled. Configure Supabase later for hosted production auth.</p>
  </section></main>
}