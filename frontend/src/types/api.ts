export type UserRole = 'participant' | 'organizer'

export type QuizStatus = 'draft' | 'published' | 'archived'

export type SessionStatus = 'waiting' | 'active' | 'ended'

export type PlaybackMode = 'manual' | 'automatic'

export interface User {
  id: string
  email: string
  display_name: string | null
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
  scoring_mode: 'standard'
  playback_mode: PlaybackMode
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
  duration_seconds: number
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
  duration_seconds: number
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

export interface SessionContext {
  session: Session
  participant: SessionParticipant | null
}

export interface QuestionEvent {
  id: string
  session_id: string
  question_id: string
  status: 'scheduled' | 'active' | 'closed'
  started_at: string | null
  ended_at: string | null
}

export interface CurrentQuestionAnswer {
  id: string
  text: string
  position: number
}

export interface CurrentQuestion {
  event_id: string
  session_id: string
  question_id: string
  type: QuestionType
  choice_mode: ChoiceMode
  text: string
  image_url: string | null
  ends_at: string | null
  shuffle_answers: boolean
  answers: CurrentQuestionAnswer[]
}

export interface QuestionAnswer {
  id: string
  participant_id: string
  question_event_id: string
  selected_answer_ids: string[]
  text_answer: string | null
  awarded_points: number
  submitted_at: string
}

export interface ScoreboardEntry {
  participant_id: string
  display_name: string
  score: number
  rank: number
}

export interface SessionScoreboard {
  session_id: string
  status: SessionStatus
  entries: ScoreboardEntry[]
  winner_ids: string[]
}

export interface ParticipantSessionHistory {
  session_id: string
  quiz_id: string
  quiz_title: string
  ended_at: string
  score: number
  rank: number
  participant_count: number
}

export interface OrganizerSessionHistory {
  session_id: string
  quiz_id: string
  quiz_title: string
  ended_at: string
  participant_count: number
  winner_names: string[]
}

export interface SessionResult {
  session_id: string
  quiz_id: string
  quiz_title: string
  organizer_id: string
  ended_at: string
  participant_count: number
  entries: ScoreboardEntry[]
  winner_ids: string[]
}

export interface ApiError {
  detail: string | ApiValidationIssue[]
}
