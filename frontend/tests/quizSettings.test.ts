import assert from 'node:assert/strict'

import { orderQuizItems } from '../src/features/quizSettings.js'

const items = ['first', 'second', 'third']
assert.deepEqual(orderQuizItems(items, false), items)
assert.notEqual(orderQuizItems(items, false), items)
assert.deepEqual(orderQuizItems(items, true, () => 0), ['second', 'third', 'first'])
assert.deepEqual(items, ['first', 'second', 'third'])
