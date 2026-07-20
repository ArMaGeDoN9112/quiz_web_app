import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'

import { AppShell } from '../components/AppShell'
import { GlassPanel } from '../components/GlassPanel'
import { ParticleField } from '../components/ParticleField'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { hasSessionEnded } from '../features/sessionLifecycle'
import { orderQuizItems } from '../features/quizSettings'
import { useLiveScoreboard } from '../features/useLiveScoreboard'
import type { CurrentQuestion, SessionParticipant, SessionScoreboard } from '../types/api'

export function ParticipantRoomPage() {
  const { sessionId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { user, loading } = useAuth()
  const [participant, setParticipant] = useState<SessionParticipant | null>(
    (location.state as { participant?: SessionParticipant } | null)?.participant ?? null,
  )
  const [roomCode, setRoomCode] = useState<string | null>(null)
  const [scoreboard, setScoreboard] = useState<SessionScoreboard | null>(null)
  const [currentQuestion, setCurrentQuestion] = useState<CurrentQuestion | null>(null)
  const [selectedAnswerIds, setSelectedAnswerIds] = useState<string[]>([])
  const [answerMessage, setAnswerMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submittedEventId, setSubmittedEventId] = useState<string | null>(null)

  useEffect(() => {
    if (!loading && (!user || user.role !== 'participant')) navigate('/login')
  }, [user, loading, navigate])

  useEffect(() => {
    if (loading || !user || user.role !== 'participant' || !sessionId) return
    let active = true
    void api.getSessionContext(sessionId)
      .then((context) => {
        if (!active) return
        if (context.participant === null) {
          navigate('/join', { replace: true })
          return
        }
        setParticipant(context.participant)
        setRoomCode(context.session.room_code)
      })
      .catch(() => {
        if (active) navigate('/join', { replace: true })
      })
    return () => { active = false }
  }, [loading, navigate, sessionId, user])

  const handleScoreboard = useCallback((nextScoreboard: SessionScoreboard) => {
    setScoreboard(nextScoreboard)
    if (hasSessionEnded(nextScoreboard)) navigate('/', { replace: true })
  }, [navigate])

  useLiveScoreboard(sessionId, roomCode ?? undefined, handleScoreboard)

  useEffect(() => {
    if (!sessionId || !participant) return
    let active = true
    const loadRoom = async () => {
      try {
        const nextQuestion = await api.getCurrentQuestion(sessionId)
        if (active) {
          setCurrentQuestion((current) => (
            current?.event_id === nextQuestion.event_id
              ? current
              : {
                  ...nextQuestion,
                  answers: orderQuizItems(nextQuestion.answers, nextQuestion.shuffle_answers),
                }
          ))
        }
      } catch {
        if (active) setCurrentQuestion(null)
      }
    }
    void loadRoom()
    const interval = window.setInterval(loadRoom, 2000)
    return () => {
      active = false
      window.clearInterval(interval)
    }
  }, [navigate, participant, sessionId])

  useEffect(() => {
    setSelectedAnswerIds([])
    setAnswerMessage('')
    setSubmittedEventId(null)
  }, [currentQuestion?.event_id])

  const toggleAnswer = (answerId: string) => {
    if (!currentQuestion || submittedEventId === currentQuestion.event_id) return
    if (currentQuestion.choice_mode === 'single') {
      setSelectedAnswerIds([answerId])
      return
    }
    setSelectedAnswerIds((current) => (
      current.includes(answerId) ? current.filter((id) => id !== answerId) : [...current, answerId]
    ))
  }

  const submitAnswer = async () => {
    if (!sessionId || !currentQuestion || selectedAnswerIds.length === 0) return
    setSubmitting(true)
    setAnswerMessage('')
    try {
      const response = await api.submitAnswer(sessionId, currentQuestion.question_id, selectedAnswerIds)
      setSubmittedEventId(currentQuestion.event_id)
      setAnswerMessage(`Answer saved: ${response.awarded_points} pts`)
    } catch (error) {
      setAnswerMessage(error instanceof Error ? error.message : 'Could not submit answer')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading || !user || !participant) {
    return <AppShell><div className="p-12 text-center font-body text-muted">Loading…</div></AppShell>
  }

  const answerSubmitted = submittedEventId === currentQuestion?.event_id

  return (
    <AppShell>
      <ParticleField />
      <section className="mx-auto flex min-h-[calc(100vh-73px)] max-w-2xl flex-col items-center justify-center px-6 py-12">
        <GlassPanel glow="violet" className="w-full text-center">
          <p className="font-body text-xs uppercase tracking-[0.35em] text-violet">Connected</p>
          <h1 className="mt-3 font-display text-2xl text-foreground">Welcome, {participant?.display_name ?? user.display_name ?? user.email}</h1>
          <p className="mt-2 font-body text-sm text-muted">Session {sessionId?.slice(0, 8)}…</p>

          {currentQuestion ? (
            <div className="my-8 rounded-xl border border-aurora/30 bg-aurora/5 p-6 text-left">
              <p className="font-body text-xs uppercase tracking-[0.25em] text-aurora">Question active</p>
              <h2 className="mt-3 font-display text-xl text-foreground">{currentQuestion.text}</h2>
              {currentQuestion.image_url && <img src={currentQuestion.image_url} alt="Question" className="mt-4 max-h-72 w-full rounded-lg object-contain" />}
              <div className="mt-5 space-y-3">
                {currentQuestion.answers.map((answer) => {
                  const selected = selectedAnswerIds.includes(answer.id)
                  return (
                    <button key={answer.id} type="button" onClick={() => toggleAnswer(answer.id)} disabled={answerSubmitted} className={`w-full rounded-xl border p-4 text-left font-body transition ${selected ? 'border-aurora bg-aurora/15 text-foreground' : 'border-white/10 bg-void/40 text-muted'}`}>
                      {answer.text}
                    </button>
                  )
                })}
              </div>
              <button type="button" onClick={submitAnswer} disabled={submitting || answerSubmitted || selectedAnswerIds.length === 0} className="btn-primary mt-5 w-full">
                {answerSubmitted ? 'Answer submitted' : submitting ? 'Submitting…' : 'Submit answer'}
              </button>
              {answerMessage && <p className="mt-3 font-body text-sm text-aurora">{answerMessage}</p>}
            </div>
          ) : (
            <div className="my-10 flex flex-col items-center gap-4">
              <div className="pulse-ring flex h-28 w-28 items-center justify-center rounded-full border border-aurora/40 bg-aurora/5"><span className="font-display text-xs tracking-[0.25em] text-aurora">STANDBY</span></div>
              <p className="font-body text-sm text-muted">Waiting for host to start a question.</p>
            </div>
          )}

          <div className="rounded-xl border border-white/15 bg-void/40 p-5 text-left">
            <p className="font-display text-sm text-foreground">Your live score</p>
            {scoreboard?.entries.filter((entry) => entry.participant_id === participant?.id).map((entry) => (
              <p key={entry.participant_id} className="mt-3 font-body text-sm text-aurora">{entry.score} pts · rank #{entry.rank}</p>
            ))}
            {!participant && <p className="mt-3 font-body text-sm text-muted">Score updates after joining.</p>}
          </div>

          <Link to="/join" className="btn-ghost mt-8 inline-block">Join another room</Link>
        </GlassPanel>
      </section>
    </AppShell>
  )
}
