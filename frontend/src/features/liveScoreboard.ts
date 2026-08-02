import type { CurrentQuestion, SessionLiveUpdate, SessionParticipant, SessionScoreboard, SessionStatus } from '../types/api.js'

const sessionStatuses = new Set<SessionStatus>(['waiting', 'active', 'ended'])

export function createScoreboardWebSocketUrl(apiUrl: string, roomCode: string, token: string): string {
  const url = new URL(apiUrl)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.pathname = `${url.pathname.replace(/\/$/, '')}/ws/sessions/${encodeURIComponent(roomCode)}`
  url.search = ''
  url.searchParams.set('token', token)
  return url.toString()
}

export function parseSessionUpdate(message: string): SessionLiveUpdate | null {
  try {
    const payload: unknown = JSON.parse(message)
    if (!isRecord(payload) || payload.type !== 'session.updated' || !isScoreboard(payload.scoreboard)) return null
    if (payload.current_question !== null && !isCurrentQuestion(payload.current_question)) return null
    return {
      scoreboard: payload.scoreboard,
      current_question: payload.current_question,
    }
  } catch {
    return null
  }
}

export function parseParticipantsUpdate(message: string): SessionParticipant[] | null {
  try {
    const payload: unknown = JSON.parse(message)
    if (!isRecord(payload) || payload.type !== 'participants.updated' || !Array.isArray(payload.participants)) return null
    return payload.participants.every(isSessionParticipant) ? payload.participants : null
  } catch {
    return null
  }
}

export function parseCommandResult(message: string): { request_id: string; detail: string | null } | null {
  try {
    const payload: unknown = JSON.parse(message)
    if (!isRecord(payload) || typeof payload.request_id !== 'string') return null
    if (payload.type === 'command.accepted') return { request_id: payload.request_id, detail: null }
    if (payload.type === 'command.error' && typeof payload.detail === 'string') {
      return { request_id: payload.request_id, detail: payload.detail }
    }
    return null
  } catch {
    return null
  }
}

function isScoreboard(scoreboard: unknown): scoreboard is SessionScoreboard {
  if (!isRecord(scoreboard)) return false
  return (
    typeof scoreboard.session_id === 'string'
    && typeof scoreboard.status === 'string'
    && sessionStatuses.has(scoreboard.status as SessionStatus)
    && Array.isArray(scoreboard.winner_ids)
    && scoreboard.winner_ids.every((id) => typeof id === 'string')
    && Array.isArray(scoreboard.entries)
    && scoreboard.entries.every(isScoreboardEntry)
  )
}

function isCurrentQuestion(question: unknown): question is CurrentQuestion {
  return (
    isRecord(question)
    && typeof question.event_id === 'string'
    && typeof question.session_id === 'string'
    && typeof question.question_id === 'string'
    && typeof question.type === 'string'
    && typeof question.choice_mode === 'string'
    && typeof question.text === 'string'
    && (typeof question.image_url === 'string' || question.image_url === null)
    && (typeof question.ends_at === 'string' || question.ends_at === null)
    && typeof question.shuffle_answers === 'boolean'
    && Array.isArray(question.answers)
    && question.answers.every((answer) => (
      isRecord(answer)
      && typeof answer.id === 'string'
      && typeof answer.text === 'string'
      && typeof answer.position === 'number'
    ))
  )
}

function isScoreboardEntry(entry: unknown): boolean {
  return (
    isRecord(entry)
    && typeof entry.participant_id === 'string'
    && typeof entry.display_name === 'string'
    && typeof entry.score === 'number'
    && typeof entry.rank === 'number'
  )
}

function isSessionParticipant(participant: unknown): participant is SessionParticipant {
  return (
    isRecord(participant)
    && typeof participant.id === 'string'
    && typeof participant.session_id === 'string'
    && typeof participant.user_id === 'string'
    && typeof participant.display_name === 'string'
    && typeof participant.joined_at === 'string'
  )
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
