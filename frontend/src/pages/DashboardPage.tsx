import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { api } from '../api/client'
import { AppShell } from '../components/AppShell'
import { GlassPanel } from '../components/GlassPanel'
import { ParticleField } from '../components/ParticleField'
import { useAuth } from '../context/AuthContext'
import type { Quiz } from '../types/api'

export function DashboardPage() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const [quizzes, setQuizzes] = useState<Quiz[]>([])
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [launchingId, setLaunchingId] = useState<string | null>(null)

  useEffect(() => {
    if (!loading && (!user || user.role !== 'organizer')) {
      navigate('/login')
    }
  }, [user, loading, navigate])

  useEffect(() => {
    if (user?.role === 'organizer') {
      api
        .listQuizzes()
        .then(setQuizzes)
        .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load quizzes'))
    }
  }, [user])

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const quiz = await api.createQuiz(title, description)
      setQuizzes((current) => [quiz, ...current])
      setTitle('')
      setDescription('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create quiz')
    } finally {
      setBusy(false)
    }
  }

  const handleLaunch = async (quizId: string) => {
    setLaunchingId(quizId)
    setError('')
    try {
      const session = await api.launchSession(quizId)
      navigate(`/host/${session.id}`, { state: { session } })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to launch session')
    } finally {
      setLaunchingId(null)
    }
  }

  const handleDelete = async (quizId: string) => {
    setError('')
    try {
      await api.deleteQuiz(quizId)
      setQuizzes((current) => current.filter((quiz) => quiz.id !== quizId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete quiz')
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
      <section className="mx-auto max-w-6xl px-6 py-12">
        <div className="mb-10">
          <p className="font-body text-xs uppercase tracking-[0.35em] text-aurora">
            Organizer control
          </p>
          <h1 className="mt-2 font-display text-3xl text-foreground">Quiz dashboard</h1>
        </div>

        <div className="grid gap-8 lg:grid-cols-[1fr_1.4fr]">
          <GlassPanel glow="aurora">
            <h2 className="font-display text-lg">New quiz</h2>
            <form onSubmit={handleCreate} className="mt-6 space-y-4">
              <label className="field">
                <span>Title</span>
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  placeholder="Neural networks 101"
                />
              </label>
              <label className="field">
                <span>Description</span>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  placeholder="Optional briefing for your team"
                />
              </label>
              <button type="submit" disabled={busy} className="btn-primary w-full">
                {busy ? 'Creating…' : 'Create quiz'}
              </button>
            </form>
          </GlassPanel>

          <GlassPanel glow="violet">
            <div className="mb-6 flex items-center justify-between">
              <h2 className="font-display text-lg">Your quizzes</h2>
              <span className="font-body text-xs text-muted">{quizzes.length} total</span>
            </div>

            {error && <p className="error-text mb-4">{error}</p>}

            {quizzes.length === 0 ? (
              <p className="font-body text-sm text-muted">
                No quizzes yet. Create your first one to launch a live room.
              </p>
            ) : (
              <ul className="space-y-4">
                {quizzes.map((quiz) => (
                  <li
                    key={quiz.id}
                    className="rounded-xl border border-white/8 bg-void/50 p-4 transition hover:border-aurora/30"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <h3 className="font-body font-medium text-foreground">{quiz.title}</h3>
                        {quiz.description && (
                          <p className="mt-1 font-body text-sm text-muted">{quiz.description}</p>
                        )}
                        <p className="mt-2 font-body text-xs uppercase tracking-wider text-muted">
                          {quiz.status} · {quiz.settings.time_limit_seconds}s per question
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <Link to={`/quizzes/${quiz.id}`} className="btn-ghost text-xs">
                          Edit
                        </Link>
                        <button
                          type="button"
                          onClick={() => handleLaunch(quiz.id)}
                          disabled={launchingId === quiz.id}
                          className="btn-primary text-xs"
                        >
                          {launchingId === quiz.id ? 'Launching…' : 'Launch live'}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(quiz.id)}
                          className="btn-ghost text-xs text-plasma"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </GlassPanel>
        </div>

        <p className="mt-8 font-body text-sm text-muted">
          Need to join as participant?{' '}
          <Link to="/join" className="text-aurora hover:underline">
            Enter room code
          </Link>
        </p>
      </section>
    </AppShell>
  )
}
