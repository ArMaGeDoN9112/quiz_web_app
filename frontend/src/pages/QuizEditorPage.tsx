import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { api, ApiRequestError } from '../api/client'
import { AppShell } from '../components/AppShell'
import { GlassPanel } from '../components/GlassPanel'
import { ParticleField } from '../components/ParticleField'
import { useAuth } from '../context/AuthContext'
import {
  buildQuestionPayload,
  validateQuestionDraft,
  type DraftAnswer,
  type QuestionDraft,
  type QuestionField,
  type QuestionFormErrors,
} from '../features/questionAuthoring'
import { buildQuizOrderSettingsUpdate } from '../features/quizSettings'
import type { ChoiceMode, PlaybackMode, Question, QuestionType, Quiz } from '../types/api'

let answerIndex = 0

function createDraftAnswer(text = '', isCorrect = false): DraftAnswer {
  answerIndex += 1
  return { id: `answer-${Date.now()}-${answerIndex}`, text, isCorrect }
}

function createInitialDraft(): QuestionDraft {
  return {
    type: 'text',
    choiceMode: 'single',
    text: '',
    imageUrl: '',
    points: '1',
    durationSeconds: '30',
    answers: [createDraftAnswer('', true), createDraftAnswer()],
  }
}

function draftFromQuestion(question: Question): QuestionDraft {
  return {
    type: question.type,
    choiceMode: question.choice_mode,
    text: question.text,
    imageUrl: question.image_url ?? '',
    points: String(question.points),
    durationSeconds: String(question.duration_seconds),
    answers: question.answers
      .slice()
      .sort((left, right) => left.position - right.position)
      .map((answer) => ({ id: answer.id, text: answer.text, isCorrect: answer.is_correct })),
  }
}

function backendErrors(error: unknown): QuestionFormErrors {
  if (!(error instanceof ApiRequestError)) {
    return {}
  }

  return error.details.reduce<QuestionFormErrors>((errors, detail) => {
    const field = detail.loc?.at(-1)
    if (field === 'text') errors.text = detail.msg
    if (field === 'image_url') errors.imageUrl = detail.msg
    if (field === 'points') errors.points = detail.msg
    if (field === 'duration_seconds') errors.durationSeconds = detail.msg
    if (field === 'answers') errors.answers = detail.msg
    if (detail.msg.includes('correct answer')) errors.correctAnswers = detail.msg
    if (detail.msg.includes('image_url') || detail.msg.includes('Image URL')) {
      errors.imageUrl = detail.msg
    }
    return errors
  }, {})
}

function questionKindLabel(type: QuestionType, choiceMode: ChoiceMode) {
  const typeLabel = type === 'image' ? 'Image' : 'Text'
  const choiceLabel = choiceMode === 'multiple' ? 'multiple choice' : 'single choice'
  return `${typeLabel} · ${choiceLabel}`
}

export function QuizEditorPage() {
  const { quizId } = useParams()
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const [quiz, setQuiz] = useState<Quiz | null>(null)
  const [questions, setQuestions] = useState<Question[]>([])
  const [draft, setDraft] = useState<QuestionDraft>(() => createInitialDraft())
  const [errors, setErrors] = useState<QuestionFormErrors>({})
  const [pageError, setPageError] = useState('')
  const [busy, setBusy] = useState(false)
  const [loadingEditor, setLoadingEditor] = useState(true)
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(null)
  const [playbackMode, setPlaybackMode] = useState<PlaybackMode>('manual')
  const [savingPlaybackMode, setSavingPlaybackMode] = useState(false)
  const [shuffleQuestions, setShuffleQuestions] = useState(false)
  const [shuffleAnswers, setShuffleAnswers] = useState(false)
  const [savingOrderSettings, setSavingOrderSettings] = useState(false)

  useEffect(() => {
    if (!loading && (!user || user.role !== 'organizer')) {
      navigate('/login')
    }
  }, [user, loading, navigate])

  useEffect(() => {
    if (!quizId || user?.role !== 'organizer') {
      return
    }

    setLoadingEditor(true)
    setPageError('')
    Promise.all([api.getQuiz(quizId), api.listQuestions(quizId)])
      .then(([loadedQuiz, loadedQuestions]) => {
        setQuiz(loadedQuiz)
        setQuestions(loadedQuestions)
        setPlaybackMode(loadedQuiz.settings.playback_mode)
        setShuffleQuestions(loadedQuiz.settings.shuffle_questions)
        setShuffleAnswers(loadedQuiz.settings.shuffle_answers)
      })
      .catch((err) => {
        setPageError(err instanceof Error ? err.message : 'Failed to load quiz editor')
      })
      .finally(() => setLoadingEditor(false))
  }, [quizId, user])

  const updateAnswer = (answerId: string, changes: Partial<DraftAnswer>) => {
    setDraft((current) => ({
      ...current,
      answers: current.answers.map((answer) =>
        answer.id === answerId ? { ...answer, ...changes } : answer,
      ),
    }))
  }

  const setCorrectAnswer = (answerId: string, checked: boolean) => {
    setDraft((current) => ({
      ...current,
      answers: current.answers.map((answer) => ({
        ...answer,
        isCorrect:
          current.choiceMode === 'single'
            ? answer.id === answerId
            : answer.id === answerId
              ? checked
              : answer.isCorrect,
      })),
    }))
  }

  const removeAnswer = (answerId: string) => {
    setDraft((current) => {
      if (current.answers.length <= 2) {
        return current
      }
      const answers = current.answers.filter((answer) => answer.id !== answerId)
      if (!answers.some((answer) => answer.isCorrect)) {
        answers[0] = { ...answers[0], isCorrect: true }
      }
      return { ...current, answers }
    })
  }

  const moveAnswer = (answerId: string, direction: -1 | 1) => {
    setDraft((current) => {
      const index = current.answers.findIndex((answer) => answer.id === answerId)
      const targetIndex = index + direction
      if (index < 0 || targetIndex < 0 || targetIndex >= current.answers.length) {
        return current
      }
      const answers = [...current.answers]
      const [answer] = answers.splice(index, 1)
      answers.splice(targetIndex, 0, answer)
      return { ...current, answers }
    })
  }

  const setChoiceMode = (choiceMode: ChoiceMode) => {
    setDraft((current) => {
      if (choiceMode === 'multiple') {
        return { ...current, choiceMode }
      }
      let correctSeen = false
      return {
        ...current,
        choiceMode,
        answers: current.answers.map((answer, index) => {
          if (answer.isCorrect && !correctSeen) {
            correctSeen = true
            return answer
          }
          if (!correctSeen && index === current.answers.length - 1) {
            return { ...answer, isCorrect: true }
          }
          return { ...answer, isCorrect: false }
        }),
      }
    })
  }

  const setQuestionType = (type: QuestionType) => {
    setDraft((current) => ({
      ...current,
      type,
      imageUrl: type === 'text' ? '' : current.imageUrl,
    }))
    setErrors((current) => {
      const next = { ...current }
      delete next.imageUrl
      return next
    })
  }

  const savePlaybackMode = async () => {
    if (!quizId) return
    setSavingPlaybackMode(true)
    setPageError('')
    try {
      setQuiz(await api.updateQuizPlaybackMode(quizId, playbackMode))
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'Could not save playback mode')
    } finally {
      setSavingPlaybackMode(false)
    }
  }

  const saveOrderSettings = async () => {
    if (!quizId) return
    setSavingOrderSettings(true)
    setPageError('')
    try {
      setQuiz(await api.updateQuizOrderSettings(
        quizId,
        buildQuizOrderSettingsUpdate(shuffleQuestions, shuffleAnswers),
      ))
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'Could not save question order settings')
    } finally {
      setSavingOrderSettings(false)
    }
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!quizId) {
      return
    }

    const nextErrors = validateQuestionDraft(draft)
    setErrors(nextErrors)
    setPageError('')
    if (Object.keys(nextErrors).length > 0) {
      return
    }

    setBusy(true)
    try {
      if (editingQuestionId) {
        await api.updateQuestion(quizId, editingQuestionId, buildQuestionPayload(draft))
      } else {
        await api.createQuestion(quizId, buildQuestionPayload(draft))
      }
      setQuestions(await api.listQuestions(quizId))
      setDraft(createInitialDraft())
      setEditingQuestionId(null)
      setErrors({})
    } catch (err) {
      const fieldErrors = backendErrors(err)
      setErrors(fieldErrors)
      setPageError(err instanceof Error ? err.message : 'Failed to create question')
    } finally {
      setBusy(false)
    }
  }

  const setDraftField = <T extends keyof QuestionDraft>(field: T, value: QuestionDraft[T]) => {
    setDraft((current) => ({ ...current, [field]: value }))
    setErrors((current) => {
      const next = { ...current }
      delete next[field as QuestionField]
      return next
    })
  }

  if (loading || loadingEditor) {
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
        <Link to="/dashboard" className="btn-ghost mb-8 inline-flex text-sm">
          Back to dashboard
        </Link>

        {pageError && <p className="error-text mb-6">{pageError}</p>}

        {quiz && (
          <div className="mb-8">
            <p className="font-body text-xs uppercase tracking-[0.35em] text-aurora">
              Quiz editor
            </p>
            <h1 className="mt-2 font-display text-3xl text-foreground">{quiz.title}</h1>
            {quiz.description && (
              <p className="mt-3 max-w-3xl font-body text-sm text-muted">{quiz.description}</p>
            )}
            <div className="mt-4 flex flex-wrap gap-2 font-body text-xs text-muted">
              <span className="rounded-lg border border-white/10 bg-void/50 px-3 py-2">
                {quiz.status}
              </span>
              <span className="rounded-lg border border-white/10 bg-void/50 px-3 py-2">
                {quiz.settings.time_limit_seconds}s
              </span>
              <span className="rounded-lg border border-white/10 bg-void/50 px-3 py-2">
                {quiz.settings.scoring_mode}
              </span>
              <span className="rounded-lg border border-white/10 bg-void/50 px-3 py-2">
                {quiz.settings.playback_mode} playback
              </span>
              <span className="rounded-lg border border-white/10 bg-void/50 px-3 py-2">
                Question order: {quiz.settings.shuffle_questions ? 'random' : 'fixed'}
              </span>
              <span className="rounded-lg border border-white/10 bg-void/50 px-3 py-2">
                Shuffle answers: {quiz.settings.shuffle_answers ? 'on' : 'off'}
              </span>
            </div>
          </div>
        )}

        <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <GlassPanel glow="aurora">
            <div className="mb-6 rounded-lg border border-aurora/25 bg-aurora/5 p-4">
              <label className="field">
                <span>Playback mode</span>
                <select
                  value={playbackMode}
                  onChange={(event) => setPlaybackMode(event.target.value as PlaybackMode)}
                >
                  <option value="manual">Manual — organizer starts each question</option>
                  <option value="automatic">Automatic — runs every question in order</option>
                </select>
              </label>
              <p className="mt-2 font-body text-xs text-muted">
                Automatic mode uses each question's duration and ends the session after the last question.
              </p>
              <button
                type="button"
                className="btn-ghost mt-3 text-xs"
                onClick={savePlaybackMode}
                disabled={savingPlaybackMode || playbackMode === quiz?.settings.playback_mode}
              >
                {savingPlaybackMode ? 'Saving…' : 'Save playback mode'}
              </button>
            </div>
            <div className="mb-6 rounded-lg border border-violet/25 bg-violet/5 p-4">
              <p className="font-body text-sm font-medium text-foreground">Question order</p>
              <div className="mt-3 space-y-3 font-body text-sm text-muted">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="question-order"
                    checked={!shuffleQuestions}
                    onChange={() => setShuffleQuestions(false)}
                  />
                  Fixed order
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="question-order"
                    checked={shuffleQuestions}
                    onChange={() => setShuffleQuestions(true)}
                  />
                  Random order
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={shuffleAnswers}
                    onChange={(event) => setShuffleAnswers(event.target.checked)}
                  />
                  Randomize answer options
                </label>
              </div>
              <button
                type="button"
                className="btn-ghost mt-4 text-xs"
                onClick={saveOrderSettings}
                disabled={
                  savingOrderSettings ||
                  (shuffleQuestions === quiz?.settings.shuffle_questions &&
                    shuffleAnswers === quiz?.settings.shuffle_answers)
                }
              >
                {savingOrderSettings ? 'Saving…' : 'Save order settings'}
              </button>
            </div>
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-display text-lg">{editingQuestionId ? 'Edit question' : 'Add question'}</h2>
              {editingQuestionId && (
                <button type="button" className="btn-ghost text-xs" onClick={() => {
                  setDraft(createInitialDraft())
                  setEditingQuestionId(null)
                  setErrors({})
                }}>
                  Cancel
                </button>
              )}
            </div>
            <form onSubmit={handleSubmit} className="mt-6 space-y-5">
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="field">
                  <span>Question type</span>
                  <select
                    value={draft.type}
                    onChange={(event) => setQuestionType(event.target.value as QuestionType)}
                  >
                    <option value="text">Text</option>
                    <option value="image">Image</option>
                  </select>
                </label>
                <label className="field">
                  <span>Choice mode</span>
                  <select
                    value={draft.choiceMode}
                    onChange={(event) => setChoiceMode(event.target.value as ChoiceMode)}
                  >
                    <option value="single">Single choice</option>
                    <option value="multiple">Multiple choice</option>
                  </select>
                </label>
              </div>

              <label className="field">
                <span>Prompt</span>
                <textarea
                  value={draft.text}
                  onChange={(event) => setDraftField('text', event.target.value)}
                  rows={4}
                  placeholder="What should participants answer?"
                />
                {errors.text && <strong className="text-xs font-medium text-plasma">{errors.text}</strong>}
              </label>

              <div className="grid gap-4 sm:grid-cols-[1fr_160px_160px]">
                <label className="field">
                  <span>Image URL</span>
                  <input
                    value={draft.imageUrl}
                    onChange={(event) => setDraftField('imageUrl', event.target.value)}
                    placeholder="https://example.com/image.png"
                    disabled={draft.type === 'text'}
                  />
                  {errors.imageUrl && (
                    <strong className="text-xs font-medium text-plasma">{errors.imageUrl}</strong>
                  )}
                </label>
                <label className="field">
                  <span>Points</span>
                  <input
                    value={draft.points}
                    onChange={(event) => setDraftField('points', event.target.value)}
                    inputMode="numeric"
                  />
                  {errors.points && (
                    <strong className="text-xs font-medium text-plasma">{errors.points}</strong>
                  )}
                </label>
                <label className="field">
                  <span>Duration (sec)</span>
                  <input
                    value={draft.durationSeconds}
                    onChange={(event) => setDraftField('durationSeconds', event.target.value)}
                    inputMode="numeric"
                    min="5"
                    max="3600"
                  />
                  {errors.durationSeconds && (
                    <strong className="text-xs font-medium text-plasma">{errors.durationSeconds}</strong>
                  )}
                </label>
              </div>

              <div>
                <div className="mb-3 flex items-center justify-between gap-3">
                  <h3 className="font-body text-sm font-medium text-foreground">Answer options</h3>
                  <button
                    type="button"
                    onClick={() =>
                      setDraft((current) => ({
                        ...current,
                        answers: [...current.answers, createDraftAnswer()],
                      }))
                    }
                    disabled={draft.answers.length >= 20}
                    className="btn-ghost text-xs"
                  >
                    Add option
                  </button>
                </div>

                <div className="space-y-3">
                  {draft.answers.map((answer, index) => (
                    <div
                      key={answer.id}
                      className="grid gap-3 rounded-lg border border-white/10 bg-void/50 p-3 sm:grid-cols-[auto_1fr_auto]"
                    >
                      <label className="flex items-center gap-2 font-body text-xs text-muted">
                        <input
                          type={draft.choiceMode === 'single' ? 'radio' : 'checkbox'}
                          name="correct-answer"
                          checked={answer.isCorrect}
                          onChange={(event) => setCorrectAnswer(answer.id, event.target.checked)}
                        />
                        Correct
                      </label>
                      <input
                        value={answer.text}
                        onChange={(event) => updateAnswer(answer.id, { text: event.target.value })}
                        placeholder={`Option ${index + 1}`}
                      />
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => moveAnswer(answer.id, -1)}
                          disabled={index === 0}
                          className="btn-ghost px-3 text-xs"
                        >
                          Up
                        </button>
                        <button
                          type="button"
                          onClick={() => moveAnswer(answer.id, 1)}
                          disabled={index === draft.answers.length - 1}
                          className="btn-ghost px-3 text-xs"
                        >
                          Down
                        </button>
                        <button
                          type="button"
                          onClick={() => removeAnswer(answer.id)}
                          disabled={draft.answers.length <= 2}
                          className="btn-ghost px-3 text-xs text-plasma"
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
                {errors.answers && <p className="mt-2 text-xs font-medium text-plasma">{errors.answers}</p>}
                {errors.correctAnswers && (
                  <p className="mt-2 text-xs font-medium text-plasma">{errors.correctAnswers}</p>
                )}
              </div>

              <button type="submit" disabled={busy} className="btn-primary w-full">
                {busy ? 'Saving…' : editingQuestionId ? 'Save changes' : 'Save question'}
              </button>
            </form>
          </GlassPanel>

          <GlassPanel glow="violet">
            <div className="mb-6 flex items-center justify-between">
              <h2 className="font-display text-lg">Questions</h2>
              <span className="font-body text-xs text-muted">{questions.length} total</span>
            </div>

            {questions.length === 0 ? (
              <p className="font-body text-sm text-muted">No questions yet.</p>
            ) : (
              <ol className="space-y-4">
                {questions.map((question) => (
                  <li key={question.id} className="rounded-lg border border-white/10 bg-void/50 p-4">
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <span className="font-body text-xs uppercase tracking-wider text-aurora">
                        Question {question.position}
                      </span>
                      <div className="flex items-center gap-3">
                        <span className="font-body text-xs text-muted">{question.points} pt · {question.duration_seconds}s</span>
                        <button type="button" className="btn-ghost text-xs" onClick={() => {
                          setDraft(draftFromQuestion(question))
                          setEditingQuestionId(question.id)
                          setErrors({})
                          setPageError('')
                        }}>
                          Edit
                        </button>
                      </div>
                    </div>
                    <h3 className="font-body text-sm font-medium text-foreground">{question.text}</h3>
                    <p className="mt-2 font-body text-xs text-muted">
                      {questionKindLabel(question.type, question.choice_mode)}
                    </p>
                    {question.image_url && (
                      <a
                        href={question.image_url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-2 block truncate font-body text-xs text-aurora hover:underline"
                      >
                        {question.image_url}
                      </a>
                    )}
                    <ul className="mt-3 space-y-2">
                      {question.answers
                        .slice()
                        .sort((left, right) => left.position - right.position)
                        .map((answer) => (
                          <li
                            key={answer.id}
                            className="flex items-center justify-between gap-3 font-body text-xs text-muted"
                          >
                            <span>{answer.text}</span>
                            {answer.is_correct && <span className="text-aurora">Correct</span>}
                          </li>
                        ))}
                    </ul>
                  </li>
                ))}
              </ol>
            )}
          </GlassPanel>
        </div>
      </section>
    </AppShell>
  )
}
