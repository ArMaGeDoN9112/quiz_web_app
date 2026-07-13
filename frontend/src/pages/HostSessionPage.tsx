import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'

import { AppShell } from '../components/AppShell'
import { GlassPanel } from '../components/GlassPanel'
import { ParticleField } from '../components/ParticleField'
import { RoomCodeDisplay } from '../components/RoomCodeDisplay'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import type { Session, SessionScoreboard } from '../types/api'

export function HostSessionPage() {
  const { sessionId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { user, loading } = useAuth()
  const session = (location.state as { session?: Session } | null)?.session
  const [scoreboard, setScoreboard] = useState<SessionScoreboard | null>(null)
  const [scoreboardError, setScoreboardError] = useState('')

  useEffect(() => {
    if (!loading && (!user || user.role !== 'organizer')) {
      navigate('/login')
    }
  }, [user, loading, navigate])

  useEffect(() => {
    if (!session) return
    let active = true
    const loadScoreboard = async () => {
      try {
        const nextScoreboard = await api.getSessionScoreboard(session.id)
        if (active) setScoreboard(nextScoreboard)
      } catch (error) {
        if (active) setScoreboardError(error instanceof Error ? error.message : 'Scoreboard unavailable')
      }
    }
    void loadScoreboard()
    const interval = window.setInterval(loadScoreboard, 2000)
    return () => {
      active = false
      window.clearInterval(interval)
    }
  }, [session])

  const endSession = async () => {
    if (!session) return
    try {
      setScoreboard(await api.endSession(session.id))
      setScoreboardError('')
    } catch (error) {
      setScoreboardError(error instanceof Error ? error.message : 'Could not end session')
    }
  }

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

          <div className="rounded-xl border border-white/15 bg-void/40 p-6 text-left">
            <div className="flex items-center justify-between gap-4">
              <p className="font-display text-sm text-foreground">Live scoreboard</p>
              {scoreboard?.status !== 'ended' && (
                <button type="button" className="btn-ghost" onClick={endSession}>
                  End session
                </button>
              )}
            </div>
            {scoreboardError && <p className="mt-3 font-body text-sm text-rose-300">{scoreboardError}</p>}
            <ol className="mt-4 space-y-2">
              {scoreboard?.entries.map((entry) => (
                <li key={entry.participant_id} className="flex justify-between font-body text-sm text-muted">
                  <span>#{entry.rank} {entry.display_name}</span>
                  <span>{entry.score} pts</span>
                </li>
              ))}
              {!scoreboard?.entries.length && <li className="font-body text-sm text-muted">No participants yet.</li>}
            </ol>
            {scoreboard?.status === 'ended' && (
              <p className="mt-4 font-body text-sm text-aurora">Final results saved.</p>
            )}
          </div>

          <Link to="/dashboard" className="btn-ghost mt-8 inline-block">
            Back to dashboard
          </Link>
        </GlassPanel>
      </section>
    </AppShell>
  )
}
