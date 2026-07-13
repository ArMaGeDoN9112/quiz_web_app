import assert from 'node:assert/strict'

import { hasSessionEnded } from '../src/features/sessionLifecycle.js'

assert.equal(hasSessionEnded({ session_id: 'session', status: 'ended', entries: [], winner_ids: [] }), true)
assert.equal(hasSessionEnded({ session_id: 'session', status: 'active', entries: [], winner_ids: [] }), false)
