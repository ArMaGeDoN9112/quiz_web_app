import type { SessionScoreboard } from '../types/api.js'

export function hasSessionEnded(scoreboard: SessionScoreboard): boolean {
  return scoreboard.status === 'ended'
}
