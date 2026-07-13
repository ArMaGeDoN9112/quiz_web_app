import type { ChoiceMode, QuestionCreateRequest, QuestionType } from '../types/api.js'

export interface DraftAnswer {
  id: string
  text: string
  isCorrect: boolean
}

export interface QuestionDraft {
  type: QuestionType
  choiceMode: ChoiceMode
  text: string
  imageUrl: string
  points: string
  durationSeconds: string
  answers: DraftAnswer[]
}

export type QuestionField =
  | 'text'
  | 'imageUrl'
  | 'points'
  | 'durationSeconds'
  | 'answers'
  | 'correctAnswers'

export type QuestionFormErrors = Partial<Record<QuestionField, string>>

function isHttpUrl(value: string): boolean {
  try {
    const parsed = new URL(value)
    return (parsed.protocol === 'http:' || parsed.protocol === 'https:') && Boolean(parsed.hostname)
  } catch {
    return false
  }
}

export function validateQuestionDraft(draft: QuestionDraft): QuestionFormErrors {
  const errors: QuestionFormErrors = {}
  const trimmedAnswers = draft.answers.map((answer) => answer.text.trim())
  const filledAnswerCount = trimmedAnswers.filter(Boolean).length
  const correctCount = draft.answers.filter((answer) => answer.isCorrect && answer.text.trim()).length
  const points = Number(draft.points)
  const durationSeconds = Number(draft.durationSeconds)
  const imageUrl = draft.imageUrl.trim()

  if (!draft.text.trim()) {
    errors.text = 'Question prompt is required.'
  }

  if (!Number.isInteger(points) || points < 1 || points > 1000) {
    errors.points = 'Points must be an integer from 1 to 1000.'
  }
  if (!Number.isInteger(durationSeconds) || durationSeconds < 5 || durationSeconds > 3600) {
    errors.durationSeconds = 'Duration must be an integer from 5 to 3600 seconds.'
  }

  if (draft.type === 'image') {
    if (!imageUrl) {
      errors.imageUrl = 'Image URL is required for image questions.'
    } else if (!isHttpUrl(imageUrl) || /\s/.test(imageUrl)) {
      errors.imageUrl = 'Image URL must start with http:// or https://.'
    }
  } else if (imageUrl) {
    errors.imageUrl = 'Text questions cannot include an image URL.'
  }

  if (filledAnswerCount < 2 || filledAnswerCount !== draft.answers.length) {
    errors.answers = 'Add at least two complete answer options.'
  }

  if (draft.choiceMode === 'single' && correctCount !== 1) {
    errors.correctAnswers = 'Select exactly one correct answer.'
  }

  if (draft.choiceMode === 'multiple' && correctCount < 2) {
    errors.correctAnswers = 'Select at least two correct answers.'
  }

  return errors
}

export function buildQuestionPayload(draft: QuestionDraft): QuestionCreateRequest {
  return {
    type: draft.type,
    choice_mode: draft.choiceMode,
    text: draft.text.trim(),
    image_url: draft.type === 'image' ? draft.imageUrl.trim() : null,
    points: Number(draft.points),
    duration_seconds: Number(draft.durationSeconds),
    answers: draft.answers.map((answer) => ({
      text: answer.text.trim(),
      is_correct: answer.isCorrect,
    })),
  }
}

export function isQuestionDraftValid(draft: QuestionDraft): boolean {
  return Object.keys(validateQuestionDraft(draft)).length === 0
}
