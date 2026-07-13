import assert from 'node:assert/strict'

import {
  buildQuestionPayload,
  isQuestionDraftValid,
  validateQuestionDraft,
  type QuestionDraft,
} from '../src/features/questionAuthoring.js'

const baseDraft: QuestionDraft = {
  type: 'text',
  choiceMode: 'single',
  text: '  Capital of France?  ',
  imageUrl: '',
  points: '2',
  durationSeconds: '45',
  answers: [
    { id: 'a', text: '  Paris  ', isCorrect: true },
    { id: 'b', text: 'Rome', isCorrect: false },
  ],
}

assert.equal(isQuestionDraftValid(baseDraft), true)
assert.deepEqual(buildQuestionPayload(baseDraft), {
  type: 'text',
  choice_mode: 'single',
  text: 'Capital of France?',
  image_url: null,
  points: 2,
  duration_seconds: 45,
  answers: [
    { text: 'Paris', is_correct: true },
    { text: 'Rome', is_correct: false },
  ],
})

assert.equal(
  validateQuestionDraft({
    ...baseDraft,
    answers: baseDraft.answers.map((answer) => ({ ...answer, isCorrect: true })),
  }).correctAnswers,
  'Select exactly one correct answer.',
)

assert.equal(
  validateQuestionDraft({
    ...baseDraft,
    choiceMode: 'multiple',
    answers: [
      { id: 'a', text: 'Mercury', isCorrect: true },
      { id: 'b', text: 'Venus', isCorrect: false },
      { id: 'c', text: 'Mars', isCorrect: false },
    ],
  }).correctAnswers,
  'Select at least two correct answers.',
)

assert.equal(
  validateQuestionDraft({
    ...baseDraft,
    type: 'image',
    imageUrl: 'javascript:alert(1)',
  }).imageUrl,
  'Image URL must start with http:// or https://.',
)

assert.deepEqual(
  buildQuestionPayload({
    ...baseDraft,
    type: 'image',
    choiceMode: 'multiple',
    imageUrl: ' https://example.com/cells.png ',
    answers: [
      { id: 'a', text: 'Cell wall', isCorrect: true },
      { id: 'b', text: 'Nucleus', isCorrect: true },
      { id: 'c', text: 'Asteroid', isCorrect: false },
    ],
  }),
  {
    type: 'image',
    choice_mode: 'multiple',
    text: 'Capital of France?',
    image_url: 'https://example.com/cells.png',
    points: 2,
    duration_seconds: 45,
    answers: [
      { text: 'Cell wall', is_correct: true },
      { text: 'Nucleus', is_correct: true },
      { text: 'Asteroid', is_correct: false },
    ],
  },
)

assert.equal(
  validateQuestionDraft({ ...baseDraft, durationSeconds: '4' }).durationSeconds,
  'Duration must be an integer from 5 to 3600 seconds.',
)
