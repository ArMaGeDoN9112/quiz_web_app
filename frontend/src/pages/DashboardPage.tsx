import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { api } from '../api/client'
import { AppShell } from '../components/AppShell'
import { GlassPanel } from '../components/GlassPanel'
import { ParticleField } from '../components/ParticleField'
import { useAuth } from '../context/AuthContext'
import type { OrganizerSessionHistory, ParticipantSessionHistory, Quiz } from '../types/api'

export function DashboardPage() {
  const { user, loading, updateProfile } = useAuth()
  const navigate = useNavigate()
  const [quizzes, setQuizzes] = useState<Quiz[]>([])
  const [participantHistory, setParticipantHistory] = useState<ParticipantSessionHistory[]>([])
  const [organizerHistory, setOrganizerHistory] = useState<OrganizerSessionHistory[]>([])
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [displayName, setDisplayName] = useState(user?.display_name ?? '')
  const [profileSaving, setProfileSaving] = useState(false)
  const [profileMessage, setProfileMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [launchingId, setLaunchingId] = useState<string | null>(null)

  useEffect(() => {
    if (!loading && !user) navigate('/login')
  }, [user, loading, navigate])

  useEffect(() => {
    if (!user) return
    if (user.role === 'organizer') {
      Promise.all([api.listQuizzes(), api.getOrganizerSessionHistory()])
        .then(([nextQuizzes, history]) => {
          setQuizzes(nextQuizzes)
          setOrganizerHistory(history)
        })
        .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load dashboard'))
      return
    }
    api.getParticipantSessionHistory().then(setParticipantHistory)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load history'))
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

  const saveProfile = async (event: FormEvent) => {
    event.preventDefault()
    setProfileSaving(true)
    setProfileMessage('')
    try {
      const updatedUser = await updateProfile(displayName)
      setDisplayName(updatedUser.display_name ?? '')
      setProfileMessage('Name saved.')
    } catch (err) {
      setProfileMessage(err instanceof Error ? err.message : 'Could not save name')
    } finally {
      setProfileSaving(false)
    }
  }

  if (loading || !user) {
    return <AppShell><div className="p-12 text-center font-body text-muted">Loading…</div></AppShell>
  }

  if (user.role === 'participant') {
    return (
      <AppShell>
        <ParticleField />
        <section className="mx-auto max-w-4xl px-6 py-12">
          <p className="font-body text-xs uppercase tracking-[0.35em] text-violet">Personal account</p>
          <h1 className="mt-2 font-display text-3xl text-foreground">Quiz history</h1>
          {error && <p className="error-text mt-5">{error}</p>}
          <GlassPanel glow="aurora" className="mt-8">
            <h2 className="font-display text-lg">Profile name</h2>
            <p className="mt-2 font-body text-sm text-muted">Used automatically in every live quiz.</p>
            <form onSubmit={saveProfile} className="mt-4 flex flex-wrap gap-3">
              <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} required maxLength={100} placeholder="Ada Lovelace" className="min-w-56 flex-1" />
              <button type="submit" disabled={profileSaving} className="btn-primary">{profileSaving ? 'Saving…' : 'Save name'}</button>
            </form>
            {profileMessage && <p className="mt-3 font-body text-sm text-muted">{profileMessage}</p>}
          </GlassPanel>
          <GlassPanel glow="violet" className="mt-8">
            {participantHistory.length === 0 ? <p className="font-body text-sm text-muted">No finished quizzes yet.</p> : (
              <ul className="space-y-3">
                {participantHistory.map((item) => (
                  <li key={item.session_id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-void/40 p-4">
                    <div><p className="font-body text-foreground">{item.quiz_title}</p><p className="mt-1 font-body text-xs text-muted">{new Date(item.ended_at).toLocaleString()} · {item.participant_count} participants</p></div>
                    <div className="flex items-center gap-4"><p className="font-body text-sm text-aurora">{item.score} pts · #{item.rank}</p><Link className="btn-ghost text-xs" to={`/sessions/${item.session_id}/result`}>Results</Link></div>
                  </li>
                ))}
              </ul>
            )}
          </GlassPanel>
          <Link to="/join" className="btn-primary mt-8 inline-block">Join a room</Link>
        </section>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <ParticleField />
      <section className="mx-auto max-w-6xl px-6 py-12">
        <div className="mb-10"><p className="font-body text-xs uppercase tracking-[0.35em] text-aurora">Organizer control</p><h1 className="mt-2 font-display text-3xl text-foreground">Quiz dashboard</h1></div>
        {error && <p className="error-text mb-4">{error}</p>}
        <div className="grid gap-8 lg:grid-cols-[1fr_1.4fr]">
          <GlassPanel glow="aurora"><h2 className="font-display text-lg">New quiz</h2><form onSubmit={handleCreate} className="mt-6 space-y-4"><label className="field"><span>Title</span><input value={title} onChange={(e) => setTitle(e.target.value)} required placeholder="Neural networks 101" /></label><label className="field"><span>Description</span><textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} placeholder="Optional briefing for your team" /></label><button type="submit" disabled={busy} className="btn-primary w-full">{busy ? 'Creating…' : 'Create quiz'}</button></form></GlassPanel>
          <GlassPanel glow="violet"><div className="mb-6 flex items-center justify-between"><h2 className="font-display text-lg">Your quizzes</h2><span className="font-body text-xs text-muted">{quizzes.length} total</span></div>{quizzes.length === 0 ? <p className="font-body text-sm text-muted">No quizzes yet. Create your first one to launch a live room.</p> : <ul className="space-y-4">{quizzes.map((quiz) => <li key={quiz.id} className="rounded-xl border border-white/8 bg-void/50 p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="font-body font-medium text-foreground">{quiz.title}</h3>{quiz.description && <p className="mt-1 font-body text-sm text-muted">{quiz.description}</p>}<p className="mt-2 font-body text-xs uppercase tracking-wider text-muted">{quiz.status} · {quiz.settings.time_limit_seconds}s per question</p></div><div className="flex gap-2"><Link to={`/quizzes/${quiz.id}`} className="btn-ghost text-xs">Edit</Link><button type="button" onClick={() => handleLaunch(quiz.id)} disabled={launchingId === quiz.id} className="btn-primary text-xs">{launchingId === quiz.id ? 'Launching…' : 'Launch live'}</button><button type="button" onClick={() => handleDelete(quiz.id)} className="btn-ghost text-xs text-plasma">Delete</button></div></div></li>)}</ul>}</GlassPanel>
        </div>
        <GlassPanel glow="aurora" className="mt-8"><h2 className="font-display text-lg">Conducted sessions</h2>{organizerHistory.length === 0 ? <p className="mt-4 font-body text-sm text-muted">No finished sessions yet.</p> : <ul className="mt-4 space-y-3">{organizerHistory.map((item) => <li key={item.session_id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-void/40 p-4"><div><p className="font-body text-foreground">{item.quiz_title}</p><p className="mt-1 font-body text-xs text-muted">{new Date(item.ended_at).toLocaleString()} · {item.participant_count} participants · winners: {item.winner_names.join(', ') || 'none'}</p></div><Link className="btn-ghost text-xs" to={`/sessions/${item.session_id}/result`}>Results</Link></li>)}</ul>}</GlassPanel>
      </section>
    </AppShell>
  )
}
