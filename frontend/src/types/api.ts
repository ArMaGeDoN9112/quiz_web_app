export type UserRole = 'participant' | 'organizer'

export type QuizStatus = 'draft' | 'published' | 'archived'

export type SessionStatus = 'waiting' | 'active' | 'ended'

export interface User {
  id: string
  email: string
  role: UserRole
  created_at: string
  updated_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface QuizSettings {
  time_limit_seconds: number
  shuffle_questions: boolean
  shuffle_answers: boolean
  show_correct_answers: boolean
  scoring_mode: 'standard' | 'speed_bonus'
}

export interface Quiz {
  id: string
  owner_id: string
  title: string
  description: string | null
  status: QuizStatus
  settings: QuizSettings
  created_at: string
  updated_at: string
}

export type QuestionType = 'text' | 'image'

export type ChoiceMode = 'single' | 'multiple'

export interface Answer {
  id: string
  text: string
  is_correct: boolean
  position: number
}

export interface Question {
  id: string
  quiz_id: string
  type: QuestionType
  choice_mode: ChoiceMode
  text: string
  image_url: string | null
  points: number
  position: number
  answers: Answer[]
}

export interface AnswerCreateRequest {
  text: string
  is_correct: boolean
}

export interface QuestionCreateRequest {
  type: QuestionType
  choice_mode: ChoiceMode
  text: string
  image_url: string | null
  points: number
  answers: AnswerCreateRequest[]
}

export interface ApiValidationIssue {
  loc?: (string | number)[]
  msg: string
  type?: string
}

export interface Session {
  id: string
  quiz_id: string
  organizer_id: string
  room_code: string
  status: SessionStatus
  created_at: string
  updated_at: string
  ended_at: string | null
}

export interface SessionParticipant {
  id: string
  session_id: string
  user_id: string
  display_name: string
  joined_at: string
}

export interface ApiError {
  detail: string | ApiValidationIssue[]
}
