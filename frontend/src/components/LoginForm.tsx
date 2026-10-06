import { useState } from 'react'
import type { FormEvent } from 'react'
import { useAuth } from '../auth/useAuth'

export default function LoginForm() {
  const { login, error, clearError } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    try {
      await login(email, password)
    } catch {
      // AuthContext supplies the user-facing error.
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="login-panel" aria-labelledby="login-heading">
      <p className="eyebrow">Secure access</p>
      <h1 id="login-heading">Sign in</h1>
      <p className="page-description">Use your ERP account to continue.</p>
      {error && <div className="notice notice--error" role="alert"><strong>Sign-in failed</strong><span>{error}</span></div>}
      <form className="login-form" onSubmit={submit}>
        <label>
          <span>Email</span>
          <input type="email" autoComplete="username" required value={email} onChange={(event) => { setEmail(event.target.value); clearError() }} />
        </label>
        <label>
          <span>Password</span>
          <input type="password" autoComplete="current-password" required value={password} onChange={(event) => { setPassword(event.target.value); clearError() }} />
        </label>
        <button className="primary-button" type="submit" disabled={submitting}>
          {submitting ? 'Signing in...' : 'Sign in'}
        </button>
      </form>
    </section>
  )
}