import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'

import { AppShell } from '../components/AppShell'
import { GlassPanel } from '../components/GlassPanel'
import { ParticleField } from '../components/ParticleField'
import { RoomCodeDisplay } from '../components/RoomCodeDisplay'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { hasSessionEnded } from '../features/sessionLifecycle'
import type { PlaybackMode, Question, Session, SessionScoreboard } from '../types/api'

export function HostSessionPage() {
  const { sessionId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { user, loading } = useAuth()
  const session = (location.state as { session?: Session } | null)?.session
  const [scoreboard, setScoreboard] = useState<SessionScoreboard | null>(null)
  const [scoreboardError, setScoreboardError] = useState('')
  const [questions, setQuestions] = useState<Question[]>([])
  const [usedQuestionIds, setUsedQuestionIds] = useState<string[]>([])
  const [questionId, setQuestionId] = useState('')
  const [playbackMode, setPlaybackMode] = useState<PlaybackMode>('manual')
  const [startingQuestion, setStartingQuestion] = useState(false)
  const [automaticQuestionIndex, setAutomaticQuestionIndex] = useState<number | null>(null)
  const hasMountedRef = useRef(false)
  const endRequestedRef = useRef(false)

  useEffect(() => {
    if (!loading && (!user || user.role !== 'organizer')) navigate('/login')
  }, [user, loading, navigate])

  useEffect(() => {
    if (!session) return
    let active = true
    const loadScoreboard = async () => {
      try {
        const nextScoreboard = await api.getSessionScoreboard(session.id)
        if (!active) return
        setScoreboard(nextScoreboard)
        if (hasSessionEnded(nextScoreboard)) navigate('/', { replace: true })
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
  }, [navigate, session])

  const endSessionForAll = useCallback((keepalive: boolean) => {
    if (!session || endRequestedRef.current) return
    endRequestedRef.current = true
    void api.endSession(session.id, keepalive)
  }, [session])

  useEffect(() => {
    if (!session) return
    const mountTimer = window.setTimeout(() => { hasMountedRef.current = true }, 0)
    const handlePageHide = () => endSessionForAll(true)
    window.addEventListener('pagehide', handlePageHide)
    return () => {
      window.clearTimeout(mountTimer)
      window.removeEventListener('pagehide', handlePageHide)
      if (hasMountedRef.current) endSessionForAll(true)
    }
  }, [endSessionForAll, session])

  useEffect(() => {
    if (!session) return
    Promise.all([api.listQuestions(session.quiz_id), api.getQuiz(session.quiz_id)])
      .then(([nextQuestions, quiz]) => {
        setQuestions(nextQuestions)
        setQuestionId(nextQuestions[0]?.id ?? '')
        setPlaybackMode(quiz.settings.playback_mode)
      })
      .catch((error) => {
        setScoreboardError(error instanceof Error ? error.message : 'Questions unavailable')
      })
  }, [session])

  const endSession = useCallback(async () => {
    if (!session) return
    endRequestedRef.current = true
    setAutomaticQuestionIndex(null)
    try {
      const finalScoreboard = await api.endSession(session.id)
      setScoreboard(finalScoreboard)
      setScoreboardError('')
      navigate('/', { replace: true })
    } catch (error) {
      setScoreboardError(error instanceof Error ? error.message : 'Could not end session')
    }
  }, [navigate, session])

  const startManualQuestion = async () => {
    if (!session || !questionId) return
    setStartingQuestion(true)
    try {
      await api.startQuestion(session.id, questionId)
      setUsedQuestionIds((current) => [...current, questionId])
      setQuestionId(questions.find((question) => question.id !== questionId && !usedQuestionIds.includes(question.id))?.id ?? '')
      setScoreboardError('')
    } catch (error) {
      setScoreboardError(error instanceof Error ? error.message : 'Could not start question')
    } finally {
      setStartingQuestion(false)
    }
  }

  const startAutomaticQuiz = async () => {
    if (!session || questions.length === 0) return
    setStartingQuestion(true)
    try {
      await api.startQuestion(session.id, questions[0].id, questions[0].duration_seconds)
      setAutomaticQuestionIndex(0)
      setScoreboardError('')
    } catch (error) {
      setScoreboardError(error instanceof Error ? error.message : 'Could not start automatic quiz')
    } finally {
      setStartingQuestion(false)
    }
  }

  useEffect(() => {
    if (!session || playbackMode !== 'automatic' || automaticQuestionIndex === null) return
    const currentQuestion = questions[automaticQuestionIndex]
    if (!currentQuestion) return
    const timer = window.setTimeout(() => {
      void (async () => {
        const nextIndex = automaticQuestionIndex + 1
        try {
          if (nextIndex >= questions.length) {
            await endSession()
            return
          }
          const nextQuestion = questions[nextIndex]
          await api.startQuestion(session.id, nextQuestion.id, nextQuestion.duration_seconds)
          setAutomaticQuestionIndex(nextIndex)
          setScoreboardError('')
        } catch (error) {
          setAutomaticQuestionIndex(null)
          setScoreboardError(error instanceof Error ? error.message : 'Could not continue automatic quiz')
        }
      })()
    }, currentQuestion.duration_seconds * 1000)
    return () => window.clearTimeout(timer)
  }, [automaticQuestionIndex, endSession, playbackMode, questions, session])

  const availableQuestions = questions.filter((question) => !usedQuestionIds.includes(question.id))
  const automaticRunning = automaticQuestionIndex !== null

  if (loading || !user || !session) {
    return (
      <AppShell>
        <div className="flex min-h-[calc(100vh-73px)] flex-col items-center justify-center gap-4 px-6">
          <p className="font-body text-muted">{session ? 'Loading…' : 'Session not found. Launch from dashboard.'}</p>
          {!session && <Link to="/dashboard" className="btn-primary">Back to dashboard</Link>}
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <ParticleField />
      <section className="mx-auto flex min-h-[calc(100vh-73px)] max-w-3xl flex-col items-center justify-center px-6 py-12">
        <GlassPanel glow="aurora" className="w-full text-center">
          <p className="font-body text-xs uppercase tracking-[0.35em] text-aurora">Live session active</p>
          <h1 className="mt-3 font-display text-2xl text-foreground">Room is open</h1>
          <p className="mt-2 font-body text-sm text-muted">Session {sessionId?.slice(0, 8)}… · {playbackMode} playback</p>
          <div className="my-10"><RoomCodeDisplay code={session.room_code} /></div>

          {scoreboard?.status !== 'ended' && (
            <div className="mb-6 rounded-xl border border-aurora/25 bg-aurora/5 p-5 text-left">
              <p className="font-display text-sm text-foreground">
                {playbackMode === 'automatic' ? 'Automatic quiz' : 'Start question'}
              </p>
              {playbackMode === 'automatic' ? (
                questions.length === 0 ? (
                  <p className="mt-3 font-body text-sm text-muted">Add questions to this quiz before starting.</p>
                ) : automaticRunning ? (
                  <p className="mt-3 font-body text-sm text-muted">
                    Running question {automaticQuestionIndex + 1} of {questions.length}. Next question starts automatically.
                  </p>
                ) : (
                  <div className="mt-4 flex flex-wrap items-center gap-3">
                    <button type="button" className="btn-primary" onClick={startAutomaticQuiz} disabled={startingQuestion}>
                      {startingQuestion ? 'Starting…' : 'Start automatic quiz'}
                    </button>
                    <span className="font-body text-xs text-muted">Questions run in position order and session ends after last.</span>
                  </div>
                )
              ) : availableQuestions.length === 0 ? (
                <p className="mt-3 font-body text-sm text-muted">
                  {questions.length === 0 ? 'Add questions to this quiz before starting.' : 'All quiz questions are complete.'}
                </p>
              ) : (
                <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto]">
                  <select value={questionId} onChange={(event) => setQuestionId(event.target.value)} className="field">
                    {availableQuestions.map((question) => <option key={question.id} value={question.id}>#{question.position} · {question.text}</option>)}
                  </select>
                  <button type="button" className="btn-primary" onClick={startManualQuestion} disabled={startingQuestion || !questionId}>
                    {startingQuestion ? 'Starting…' : 'Start question'}
                  </button>
                </div>
              )}
            </div>
          )}

          <div className="rounded-xl border border-white/15 bg-void/40 p-6 text-left">
            <div className="flex items-center justify-between gap-4">
              <p className="font-display text-sm text-foreground">Live scoreboard</p>
              {scoreboard?.status !== 'ended' && <button type="button" className="btn-ghost" onClick={endSession}>End session</button>}
            </div>
            {scoreboardError && <p className="mt-3 font-body text-sm text-rose-300">{scoreboardError}</p>}
            <ol className="mt-4 space-y-2">
              {scoreboard?.entries.map((entry) => <li key={entry.participant_id} className="flex justify-between font-body text-sm text-muted"><span>#{entry.rank} {entry.display_name}</span><span>{entry.score} pts</span></li>)}
              {!scoreboard?.entries.length && <li className="font-body text-sm text-muted">No participants yet.</li>}
            </ol>
            {scoreboard?.status === 'ended' && <p className="mt-4 font-body text-sm text-aurora">Final results saved.</p>}
          </div>
          <Link to="/dashboard" className="btn-ghost mt-8 inline-block">Back to dashboard</Link>
        </GlassPanel>
      </section>
    </AppShell>
  )
}
