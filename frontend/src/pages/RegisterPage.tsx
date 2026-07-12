import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { AppShell } from '../components/AppShell'
import { GlassPanel } from '../components/GlassPanel'
import { ParticleField } from '../components/ParticleField'
import { useAuth } from '../context/AuthContext'
import type { UserRole } from '../types/api'

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const initialRole = searchParams.get('role') === 'organizer' ? 'organizer' : 'participant'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<UserRole>(initialRole)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const user = await register(email, password, role)
      navigate(user.role === 'organizer' ? '/dashboard' : '/join')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AppShell>
      <ParticleField />
      <section className="mx-auto flex min-h-[calc(100vh-73px)] max-w-lg items-center px-6 py-12">
        <GlassPanel glow="plasma" className="w-full">
          <h1 className="font-display text-2xl text-foreground">Create account</h1>
          <p className="mt-2 font-body text-sm text-muted">
            Choose your role. Organizers build quizzes. Participants join live rooms.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <div className="grid grid-cols-2 gap-3">
              {(['organizer', 'participant'] as UserRole[]).map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setRole(option)}
                  className={`role-chip ${role === option ? 'role-chip-active' : ''}`}
                >
                  {option}
                </button>
              ))}
            </div>

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
                minLength={8}
                autoComplete="new-password"
              />
            </label>

            {error && <p className="error-text">{error}</p>}

            <button type="submit" disabled={submitting} className="btn-primary w-full">
              {submitting ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          <p className="mt-6 font-body text-sm text-muted">
            Already registered?{' '}
            <Link to="/login" className="text-plasma hover:underline">
              Sign in
            </Link>
          </p>
        </GlassPanel>
      </section>
    </AppShell>
  )
}
