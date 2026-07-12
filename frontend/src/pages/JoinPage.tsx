import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import { api } from '../api/client'
import { AppShell } from '../components/AppShell'
import { GlassPanel } from '../components/GlassPanel'
import { ParticleField } from '../components/ParticleField'
import { useAuth } from '../context/AuthContext'

export function JoinPage() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const [roomCode, setRoomCode] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!loading && !user) {
      navigate('/login')
    }
    if (!loading && user && user.role !== 'participant') {
      navigate('/dashboard')
    }
  }, [user, loading, navigate])

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const participant = await api.joinSession(roomCode, displayName)
      navigate(`/room/${participant.session_id}`, { state: { participant } })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not join session')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading || !user) {
    return (
      <AppShell>
        <div className="flex min-h-[calc(100vh-73px)] items-center justify-center font-body text-muted">
          Loading…
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <ParticleField />
      <section className="mx-auto flex min-h-[calc(100vh-73px)] max-w-lg items-center px-6 py-12">
        <GlassPanel glow="plasma" className="w-full">
          <p className="font-body text-xs uppercase tracking-[0.35em] text-plasma">
            Participant entry
          </p>
          <h1 className="mt-2 font-display text-2xl text-foreground">Join live room</h1>
          <p className="mt-2 font-body text-sm text-muted">
            Enter the code from your host screen and pick a display name.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <label className="field">
              <span>Room code</span>
              <input
                value={roomCode}
                onChange={(e) => setRoomCode(e.target.value.toUpperCase())}
                required
                placeholder="AB12CD"
                className="font-display tracking-[0.3em]"
              />
            </label>
            <label className="field">
              <span>Display name</span>
              <input
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
                placeholder="Nova"
              />
            </label>

            {error && <p className="error-text">{error}</p>}

            <button type="submit" disabled={submitting} className="btn-secondary w-full">
              {submitting ? 'Connecting…' : 'Enter room'}
            </button>
          </form>
        </GlassPanel>
      </section>
    </AppShell>
  )
}
