import type { SessionScoreboard, SessionStatus } from '../types/api.js'

const sessionStatuses = new Set<SessionStatus>(['waiting', 'active', 'ended'])

export function createScoreboardWebSocketUrl(apiUrl: string, roomCode: string, token: string): string {
  const url = new URL(apiUrl)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.pathname = `${url.pathname.replace(/\/$/, '')}/ws/sessions/${encodeURIComponent(roomCode)}`
  url.search = ''
  url.searchParams.set('token', token)
  return url.toString()
}

export function parseScoreboardUpdate(message: string): SessionScoreboard | null {
  try {
    const payload: unknown = JSON.parse(message)
    if (!isScoreboardUpdate(payload)) return null
    return payload.scoreboard
  } catch {
    return null
  }
}

function isScoreboardUpdate(payload: unknown): payload is { type: 'scoreboard.updated'; scoreboard: SessionScoreboard } {
  if (!isRecord(payload) || payload.type !== 'scoreboard.updated' || !isRecord(payload.scoreboard)) return false
  const { scoreboard } = payload
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

function isScoreboardEntry(entry: unknown): boolean {
  return (
    isRecord(entry)
    && typeof entry.participant_id === 'string'
    && typeof entry.display_name === 'string'
    && typeof entry.score === 'number'
    && typeof entry.rank === 'number'
  )
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
