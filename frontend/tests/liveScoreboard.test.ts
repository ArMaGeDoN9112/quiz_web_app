import assert from 'node:assert/strict'

import { createScoreboardWebSocketUrl, parseScoreboardUpdate } from '../src/features/liveScoreboard.js'

const scoreboard = {
  session_id: 'session',
  status: 'active',
  entries: [{ participant_id: 'participant', display_name: 'Ada', score: 3, rank: 1 }],
  winner_ids: [],
}

assert.deepEqual(
  parseScoreboardUpdate(JSON.stringify({ type: 'scoreboard.updated', scoreboard })),
  scoreboard,
)
assert.equal(parseScoreboardUpdate(JSON.stringify({ type: 'unknown' })), null)
assert.equal(parseScoreboardUpdate('not json'), null)
assert.equal(
  createScoreboardWebSocketUrl('https://quiz.example/api', 'AB C', 'token'),
  'wss://quiz.example/api/ws/sessions/AB%20C?token=token',
)
