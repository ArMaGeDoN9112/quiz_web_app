import assert from 'node:assert/strict'

import { createScoreboardWebSocketUrl, parseCommandResult, parseSessionUpdate } from '../src/features/liveScoreboard.js'

const scoreboard = {
  session_id: 'session',
  status: 'active',
  entries: [{ participant_id: 'participant', display_name: 'Ada', score: 3, rank: 1 }],
  winner_ids: [],
}

assert.deepEqual(
  parseSessionUpdate(JSON.stringify({ type: 'session.updated', scoreboard, current_question: null })),
  { scoreboard, current_question: null },
)
assert.equal(parseSessionUpdate(JSON.stringify({ type: 'session.updated', scoreboard })), null)
assert.deepEqual(
  parseCommandResult(JSON.stringify({ type: 'command.accepted', request_id: 'request-1' })),
  { request_id: 'request-1', detail: null },
)
assert.deepEqual(
  parseCommandResult(JSON.stringify({ type: 'command.error', request_id: 'request-1', detail: 'Session is ended' })),
  { request_id: 'request-1', detail: 'Session is ended' },
)
assert.equal(
  createScoreboardWebSocketUrl('https://quiz.example/api', 'AB C', 'token'),
  'wss://quiz.example/api/ws/sessions/AB%20C?token=token',
)
