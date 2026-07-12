import type {
  Quiz,
  Session,
  SessionParticipant,
  TokenResponse,
  User,
  UserRole,
} from '../types/api'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

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
      try {
        const body = await response.json()
        if (typeof body.detail === 'string') {
          detail = body.detail
        } else if (Array.isArray(body.detail)) {
          detail = body.detail.map((item: { msg: string }) => item.msg).join(', ')
        }
      } catch {
        detail = response.statusText
      }
      throw new Error(detail)
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

  createQuiz(title: string, description?: string) {
    return this.request<Quiz>('/quizzes', {
      method: 'POST',
      body: JSON.stringify({ title, description: description || null }),
    })
  }

  deleteQuiz(quizId: string) {
    return this.request<void>(`/quizzes/${quizId}`, { method: 'DELETE' })
  }

  launchSession(quizId: string) {
    return this.request<Session>('/sessions', {
      method: 'POST',
      body: JSON.stringify({ quiz_id: quizId }),
    })
  }

  joinSession(roomCode: string, displayName: string) {
    return this.request<SessionParticipant>('/sessions/join', {
      method: 'POST',
      body: JSON.stringify({ room_code: roomCode, display_name: displayName }),
    })
  }
}

export const api = new ApiClient()
