import type {
  ApiValidationIssue,
  Question,
  QuestionCreateRequest,
  OrganizerSessionHistory,
  PaginationParams,
  PlaybackMode,
  ParticipantSessionHistory,
  Quiz,
  QuizSettings,
  Session,
  SessionContext,
  SessionParticipant,
  SessionResult,
  TokenResponse,
  User,
  UserRole,
} from '../types/api.js'
import { createScoreboardWebSocketUrl } from '../features/liveScoreboard.js'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const MAX_PAGE_SIZE = 100

function withPagination(path: string, { limit = 20, offset = 0 }: PaginationParams = {}): string {
  const search = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  return `${path}?${search.toString()}`
}

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

  openSessionScoreboardSocket(roomCode: string): WebSocket | null {
    if (!this.token) return null
    return new WebSocket(createScoreboardWebSocketUrl(API_URL, roomCode, this.token))
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

  listQuizzes(pagination?: PaginationParams) {
    return this.request<Quiz[]>(withPagination('/quizzes', pagination))
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

  listQuestions(quizId: string, pagination?: PaginationParams) {
    return this.request<Question[]>(
      withPagination(`/quizzes/${quizId}/questions`, pagination),
    )
  }

  async listAllQuestions(quizId: string) {
    const questions: Question[] = []
    for (let offset = 0; ; offset += MAX_PAGE_SIZE) {
      const page = await this.listQuestions(quizId, { limit: MAX_PAGE_SIZE, offset })
      questions.push(...page)
      if (page.length < MAX_PAGE_SIZE) return questions
    }
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

  getParticipantSessionHistory(pagination?: PaginationParams) {
    return this.request<ParticipantSessionHistory[]>(
      withPagination('/sessions/history/participated', pagination),
    )
  }

  getOrganizerSessionHistory(pagination?: PaginationParams) {
    return this.request<OrganizerSessionHistory[]>(
      withPagination('/sessions/history/conducted', pagination),
    )
  }

  getSessionResult(sessionId: string) {
    return this.request<SessionResult>(`/sessions/${sessionId}/result`)
  }
}

export const api = new ApiClient()
