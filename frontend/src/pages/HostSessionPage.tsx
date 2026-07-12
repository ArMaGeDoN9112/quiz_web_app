import { useEffect } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'

import { AppShell } from '../components/AppShell'
import { GlassPanel } from '../components/GlassPanel'
import { ParticleField } from '../components/ParticleField'
import { RoomCodeDisplay } from '../components/RoomCodeDisplay'
import { useAuth } from '../context/AuthContext'
import type { Session } from '../types/api'

export function HostSessionPage() {
  const { sessionId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { user, loading } = useAuth()
  const session = (location.state as { session?: Session } | null)?.session

  useEffect(() => {
    if (!loading && (!user || user.role !== 'organizer')) {
      navigate('/login')
    }
  }, [user, loading, navigate])

  if (loading || !user || !session) {
    return (
      <AppShell>
        <div className="flex min-h-[calc(100vh-73px)] flex-col items-center justify-center gap-4 px-6">
          <p className="font-body text-muted">
            {session ? 'Loading…' : 'Session not found. Launch from dashboard.'}
          </p>
          {!session && (
            <Link to="/dashboard" className="btn-primary">
              Back to dashboard
            </Link>
          )}
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <ParticleField />
      <section className="mx-auto flex min-h-[calc(100vh-73px)] max-w-3xl flex-col items-center justify-center px-6 py-12">
        <GlassPanel glow="aurora" className="w-full text-center">
          <p className="font-body text-xs uppercase tracking-[0.35em] text-aurora">
            Live session active
          </p>
          <h1 className="mt-3 font-display text-2xl text-foreground">Room is open</h1>
          <p className="mt-2 font-body text-sm text-muted">
            Session {sessionId?.slice(0, 8)}… · status {session.status}
          </p>

          <div className="my-10">
            <RoomCodeDisplay code={session.room_code} />
          </div>

          <div className="rounded-xl border border-dashed border-white/15 bg-void/40 p-6">
            <p className="font-body text-sm text-muted">
              Question controls and scoreboard sync arrive in the next phase.
              Participants can join now with the room code above.
            </p>
          </div>

          <Link to="/dashboard" className="btn-ghost mt-8 inline-block">
            Back to dashboard
          </Link>
        </GlassPanel>
      </section>
    </AppShell>
  )
}
