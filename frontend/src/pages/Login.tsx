import { useState } from 'react'
import { useAuthStore } from '../store/auth'

const label: React.CSSProperties = { display: 'block', fontSize: 11, fontWeight: 700, color: 'var(--navy)', textTransform: 'uppercase', letterSpacing: '.5px', marginBottom: 6 }
const input = (err: boolean): React.CSSProperties => ({
  width: '100%', padding: '12px 14px', borderRadius: 9, border: `1.5px solid ${err ? '#fca5a5' : 'var(--border)'}`,
  background: 'var(--surface2)', fontSize: 14, fontFamily: 'inherit', color: 'var(--text)', outline: 'none',
})

export default function Login() {
  const login = useAuthStore(s => s.login)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (busy) return
    setBusy(true)
    const err = await login(email.trim(), password)
    setBusy(false)
    if (err) { setError(err); setPassword('') }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(180deg, var(--surface2), var(--surface))', padding: 16 }}>
      <div style={{ background: '#fff', borderRadius: 18, padding: '48px 44px 40px', width: '100%', maxWidth: 440, boxShadow: '0 8px 40px rgba(12,26,46,.10), 0 2px 8px rgba(12,26,46,.06)' }}>
        <div style={{ marginBottom: 30 }}>
          <div style={{ fontFamily: 'var(--f-display)', fontSize: 26, fontWeight: 700, color: 'var(--navy)', lineHeight: 1.25, marginBottom: 8 }}>
            Venture GP <span style={{ color: 'var(--gold)' }}>·</span> Atlas
          </div>
          <div style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '1.4px', color: 'var(--subtle)', textTransform: 'uppercase' }}>
            Mindari · VC &amp; growth manager tracker
          </div>
        </div>
        <form onSubmit={submit} noValidate>
          <div style={{ marginBottom: 16 }}>
            <label htmlFor="email" style={label}>Email</label>
            <input id="email" type="email" autoFocus autoComplete="username" value={email} disabled={busy}
              onChange={e => { setEmail(e.target.value); setError(null) }} placeholder="you@company.com" style={input(!!error)} />
          </div>
          <div style={{ marginBottom: 20 }}>
            <label htmlFor="password" style={label}>Password</label>
            <input id="password" type="password" autoComplete="current-password" value={password} disabled={busy}
              onChange={e => { setPassword(e.target.value); setError(null) }} placeholder="Your password" style={input(!!error)} />
          </div>
          {error && <div className="err-box" style={{ marginBottom: 16 }}>{error}</div>}
          <button type="submit" disabled={busy || !email || !password} className="btn btn-primary" style={{ width: '100%', padding: '13px 0', fontSize: 14, borderRadius: 10 }}>
            {busy ? 'Signing in…' : 'Sign in →'}
          </button>
        </form>
        <p className="note" style={{ marginTop: 26, textAlign: 'center' }}>Accounts are created by an admin in the Django admin panel.</p>
      </div>
    </div>
  )
}
