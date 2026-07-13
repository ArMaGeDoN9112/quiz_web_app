import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'

import { AppShell } from '../components/AppShell'
import { GlassPanel } from '../components/GlassPanel'
import { ParticleField } from '../components/ParticleField'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import type { SessionParticipant, SessionScoreboard } from '../types/api'

export function ParticipantRoomPage() {
  const { sessionId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { user, loading } = useAuth()
  const participant = (location.state as { participant?: SessionParticipant } | null)
    ?.participant
  const [scoreboard, setScoreboard] = useState<SessionScoreboard | null>(null)

  useEffect(() => {
    if (!loading && !user) {
      navigate('/login')
    }
  }, [user, loading, navigate])

  useEffect(() => {
    if (!sessionId) return
    let active = true
    const loadScoreboard = async () => {
      try {
        const nextScoreboard = await api.getSessionScoreboard(sessionId)
        if (active) setScoreboard(nextScoreboard)
      } catch {
        // The room can still be loading while the join request settles.
      }
    }
    void loadScoreboard()
    const interval = window.setInterval(loadScoreboard, 2000)
    return () => {
      active = false
      window.clearInterval(interval)
    }
  }, [sessionId])

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
      <section className="mx-auto flex min-h-[calc(100vh-73px)] max-w-2xl flex-col items-center justify-center px-6 py-12">
        <GlassPanel glow="violet" className="w-full text-center">
          <p className="font-body text-xs uppercase tracking-[0.35em] text-violet">
            Connected
          </p>
          <h1 className="mt-3 font-display text-2xl text-foreground">
            Welcome, {participant?.display_name ?? user.email}
          </h1>
          <p className="mt-2 font-body text-sm text-muted">
            Session {sessionId?.slice(0, 8)}… — waiting for host to start first question.
          </p>

          <div className="my-10 flex justify-center">
            <div className="pulse-ring relative flex h-28 w-28 items-center justify-center rounded-full border border-aurora/40 bg-aurora/5">
              <span className="font-display text-xs tracking-[0.25em] text-aurora">STANDBY</span>
            </div>
          </div>

          <div className="rounded-xl border border-white/15 bg-void/40 p-5 text-left">
            <p className="font-display text-sm text-foreground">Your live score</p>
            {scoreboard?.entries
              .filter((entry) => entry.participant_id === participant?.id)
              .map((entry) => (
                <p key={entry.participant_id} className="mt-3 font-body text-sm text-aurora">
                  {entry.score} pts · rank #{entry.rank}
                </p>
              ))}
            {!participant && <p className="mt-3 font-body text-sm text-muted">Score updates after joining.</p>}
          </div>

          <Link to="/join" className="btn-ghost mt-8 inline-block">
            Join another room
          </Link>
        </GlassPanel>
      </section>
    </AppShell>
  )
}
