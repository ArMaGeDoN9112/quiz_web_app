import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { AppShell } from '../components/AppShell'
import { GlassPanel } from '../components/GlassPanel'
import { ParticleField } from '../components/ParticleField'
import { useAuth } from '../context/AuthContext'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const user = await login(email, password)
      navigate(user.role === 'organizer' ? '/dashboard' : '/join')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign in failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AppShell>
      <ParticleField />
      <section className="mx-auto flex min-h-[calc(100vh-73px)] max-w-lg items-center px-6 py-12">
        <GlassPanel glow="violet" className="w-full">
          <h1 className="font-display text-2xl text-foreground">Sign in</h1>
          <p className="mt-2 font-body text-sm text-muted">
            Access your organizer dashboard or participant room.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <label className="field">
              <span>Email</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </label>
            <label className="field">
              <span>Password</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </label>

            {error && <p className="error-text">{error}</p>}

            <button type="submit" disabled={submitting} className="btn-primary w-full">
              {submitting ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p className="mt-6 font-body text-sm text-muted">
            No account?{' '}
            <Link to="/register" className="text-aurora hover:underline">
              Create one
            </Link>
          </p>
        </GlassPanel>
      </section>
    </AppShell>
  )
}
