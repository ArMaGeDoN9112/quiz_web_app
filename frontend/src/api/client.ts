import type {
  ApiValidationIssue,
  Question,
  CurrentQuestion,
  QuestionAnswer,
  QuestionCreateRequest,
  QuestionEvent,
  OrganizerSessionHistory,
  PlaybackMode,
  ParticipantSessionHistory,
  Quiz,
  QuizSettings,
  Session,
  SessionContext,
  SessionParticipant,
  SessionResult,
  SessionScoreboard,
  TokenResponse,
  User,
  UserRole,
} from '../types/api'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiRequestError extends Error {
  status: number
  details: ApiValidationIssue[]

  constructor(message: string, status: number, details: ApiValidationIssue[] = []) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = status
    this.details = details
  }
}

class ApiClient {
  private token: string | null = null

  setToken(token: string | null) {
    this.token = token
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
  ): Promise<T> {
    const headers = new Headers(options.headers)
    headers.set('Content-Type', 'application/json')
    if (this.token) {
      headers.set('Authorization', `Bearer ${this.token}`)
    }

    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      let detail = 'Request failed'
      let details: ApiValidationIssue[] = []
      try {
        const body = await response.json()
        if (typeof body.detail === 'string') {
          detail = body.detail
        } else if (Array.isArray(body.detail)) {
          details = body.detail
          detail = details.map((item) => item.msg).join(', ')
        }
      } catch {
        detail = response.statusText
      }
      throw new ApiRequestError(detail, response.status, details)
    }

    if (response.status === 204) {
      return undefined as T
    }

    return response.json() as Promise<T>
  }

  register(email: string, password: string, role: UserRole) {
    return this.request<User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, role }),
    })
  }

  login(email: string, password: string) {
    return this.request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  }

  getMe() {
    return this.request<User>('/users/me')
  }

  listQuizzes() {
    return this.request<Quiz[]>('/quizzes')
  }

  getQuiz(quizId: string) {
    return this.request<Quiz>(`/quizzes/${quizId}`)
  }

  createQuiz(title: string, description?: string) {
    return this.request<Quiz>('/quizzes', {
      method: 'POST',
      body: JSON.stringify({ title, description: description || null }),
    })
  }

  updateQuizPlaybackMode(quizId: string, playbackMode: PlaybackMode) {
    return this.request<Quiz>(`/quizzes/${quizId}`, {
      method: 'PATCH',
      body: JSON.stringify({ settings: { playback_mode: playbackMode } }),
    })
  }

  updateQuizOrderSettings(
    quizId: string,
    settings: Pick<QuizSettings, 'shuffle_questions' | 'shuffle_answers'>,
  ) {
    return this.request<Quiz>(`/quizzes/${quizId}`, {
      method: 'PATCH',
      body: JSON.stringify({ settings }),
    })
  }

  deleteQuiz(quizId: string) {
    return this.request<void>(`/quizzes/${quizId}`, { method: 'DELETE' })
  }

  listQuestions(quizId: string) {
    return this.request<Question[]>(`/quizzes/${quizId}/questions`)
  }

  createQuestion(quizId: string, question: QuestionCreateRequest) {
    return this.request<Question>(`/quizzes/${quizId}/questions`, {
      method: 'POST',
      body: JSON.stringify(question),
    })
  }

  updateQuestion(quizId: string, questionId: string, question: QuestionCreateRequest) {
    return this.request<Question>(`/quizzes/${quizId}/questions/${questionId}`, {
      method: 'PUT',
      body: JSON.stringify(question),
    })
  }

  launchSession(quizId: string) {
    return this.request<Session>('/sessions', {
      method: 'POST',
      body: JSON.stringify({ quiz_id: quizId }),
    })
  }

  getSessionContext(sessionId: string) {
    return this.request<SessionContext>(`/sessions/${sessionId}`)
  }

  updateProfile(displayName: string) {
    return this.request<User>('/users/me', {
      method: 'PATCH',
      body: JSON.stringify({ display_name: displayName }),
    })
  }

  joinSession(roomCode: string) {
    return this.request<SessionParticipant>('/sessions/join', {
      method: 'POST',
      body: JSON.stringify({ room_code: roomCode }),
    })
  }

  startQuestion(sessionId: string, questionId: string, durationSeconds?: number) {
    const body: { question_id: string; duration_seconds?: number } = { question_id: questionId }
    if (durationSeconds !== undefined) body.duration_seconds = durationSeconds
    return this.request<QuestionEvent>(`/sessions/${sessionId}/questions/current`, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }

  getSessionScoreboard(sessionId: string) {
    return this.request<SessionScoreboard>(`/sessions/${sessionId}/scoreboard`)
  }

  getCurrentQuestion(sessionId: string) {
    return this.request<CurrentQuestion>(`/sessions/${sessionId}/questions/current`)
  }

  submitAnswer(sessionId: string, questionId: string, selectedAnswerIds: string[]) {
    return this.request<QuestionAnswer>(`/sessions/${sessionId}/answer`, {
      method: 'POST',
      body: JSON.stringify({ question_id: questionId, selected_answer_ids: selectedAnswerIds }),
    })
  }

  endSession(sessionId: string) {
    return this.request<SessionScoreboard>(`/sessions/${sessionId}/end`, {
      method: 'POST',
    })
  }

  getParticipantSessionHistory() {
    return this.request<ParticipantSessionHistory[]>('/sessions/history/participated')
  }

  getOrganizerSessionHistory() {
    return this.request<OrganizerSessionHistory[]>('/sessions/history/conducted')
  }

  getSessionResult(sessionId: string) {
    return this.request<SessionResult>(`/sessions/${sessionId}/result`)
  }
}

export const api = new ApiClient()
