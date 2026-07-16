import assert from 'node:assert/strict'

import { buildQuizOrderSettingsUpdate, orderQuizItems } from '../src/features/quizSettings.js'

assert.deepEqual(buildQuizOrderSettingsUpdate(false, false), {
  shuffle_questions: false,
  shuffle_answers: false,
})

assert.deepEqual(buildQuizOrderSettingsUpdate(true, true), {
  shuffle_questions: true,
  shuffle_answers: true,
})

const items = ['first', 'second', 'third']
assert.deepEqual(orderQuizItems(items, false), items)
assert.notEqual(orderQuizItems(items, false), items)
assert.deepEqual(orderQuizItems(items, true, () => 0), ['second', 'third', 'first'])
assert.deepEqual(items, ['first', 'second', 'third'])
