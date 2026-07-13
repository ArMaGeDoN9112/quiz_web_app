import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { api } from '../api/client'
import { AppShell } from '../components/AppShell'
import { GlassPanel } from '../components/GlassPanel'
import { ParticleField } from '../components/ParticleField'
import { useAuth } from '../context/AuthContext'
import type { SessionResult } from '../types/api'

export function SessionResultPage() {
  const { sessionId } = useParams()
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const [result, setResult] = useState<SessionResult | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!loading && !user) navigate('/login')
  }, [loading, navigate, user])

  useEffect(() => {
    if (!user || !sessionId) return
    api.getSessionResult(sessionId).then(setResult).catch((err) => {
      setError(err instanceof Error ? err.message : 'Session result unavailable')
    })
  }, [sessionId, user])

  if (loading || !user) {
    return <AppShell><div className="p-12 text-center font-body text-muted">Loading…</div></AppShell>
  }

  return (
    <AppShell>
      <ParticleField />
      <section className="mx-auto max-w-3xl px-6 py-12">
        <GlassPanel glow="aurora">
          <p className="font-body text-xs uppercase tracking-[0.35em] text-aurora">Final results</p>
          {error && <p className="error-text mt-4">{error}</p>}
          {!error && !result && <p className="mt-4 font-body text-muted">Loading results…</p>}
          {result && (
            <>
              <h1 className="mt-2 font-display text-3xl text-foreground">{result.quiz_title}</h1>
              <p className="mt-2 font-body text-sm text-muted">
                {result.participant_count} participants · ended {new Date(result.ended_at).toLocaleString()}
              </p>
              <ol className="mt-8 space-y-3">
                {result.entries.map((entry) => (
                  <li key={entry.participant_id} className="flex items-center justify-between rounded-xl border border-white/10 bg-void/40 p-4 font-body">
                    <span className={entry.rank === 1 ? 'text-aurora' : 'text-foreground'}>
                      #{entry.rank} {entry.display_name}{result.winner_ids.includes(entry.participant_id) ? ' · Winner' : ''}
                    </span>
                    <span className="text-muted">{entry.score} pts</span>
                  </li>
                ))}
              </ol>
            </>
          )}
          <Link to="/dashboard" className="btn-ghost mt-8 inline-block">Back to dashboard</Link>
        </GlassPanel>
      </section>
    </AppShell>
  )
}
