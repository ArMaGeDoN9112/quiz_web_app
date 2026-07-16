# Quiz Web App

Monorepo for live quiz platform: FastAPI backend + React frontend.

## Structure

```
backend/    FastAPI API, PostgreSQL, Alembic migrations
frontend/   React + Vite + Tailwind UI (Neuracle)
```

## Stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2 async, PostgreSQL, Alembic, Pydantic v2

**Frontend:** React 19, TypeScript, Vite, Tailwind CSS v4, Motion

## Quick start

Copy env files:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

`backend/.env` is runtime-only: Docker loads it with `env_file`; Docker images
exclude it. Set `JWT_SECRET_KEY` to a unique random value of at least 32
characters before any non-local deployment. PostgreSQL is available only to
Docker services by default and has no host port.

Run full stack with Docker:

```bash
docker compose up --build
```

- API: http://localhost:8000/docs
- Frontend: http://localhost:5173

## Local development

Backend:

```bash
cd backend
python -m pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Tests (backend):

```bash
cd backend
python -m pytest -q
```

Build frontend:

```bash
cd frontend
npm run build
```

## API groups

- `POST /auth/register`, `POST /auth/login`
- `GET /users/me`
- `GET|POST|PATCH|DELETE /quizzes`
- `POST /sessions`, `POST /sessions/join`
- `POST /sessions/{id}/answer`
- `GET /sessions/{id}/scoreboard`, `POST /sessions/{id}/end`

Automatic playback runs in backend process: after host starts first question,
server advances timed questions and ends session after last question. PostgreSQL
row locking prevents duplicate transitions when multiple API processes run.

## Implementation Phase Plan

This plan tracks the remaining product work as small, verifiable slices. Each phase should leave the backend tests passing and the frontend buildable.

### Phase 4: Quiz And Question Authoring

- [x] Add frontend API client methods for creating questions through `POST /quizzes/{quiz_id}/questions`.
- [x] Add quiz detail/editor route from the organizer dashboard.
- [x] Show existing quiz metadata, settings, and question list in the editor.
- [x] Add question creation form for text questions.
- [x] Add question creation form support for image questions with image URL validation feedback.
- [x] Support single-choice answers with exactly one correct answer selected.
- [x] Support multiple-choice answers with at least two correct answers selected.
- [x] Let organizers add, edit before submit, remove, and reorder draft answer options in the form.
- [x] Refresh the question list after successful creation.
- [x] Display backend validation errors next to the relevant fields.
- [x] Add frontend tests or component-level checks for question form validation and submit payloads.
- [x] Document the organizer question authoring flow in frontend or product docs.
- [x] Let organizers choose manual or automatic quiz playback and set a duration for every question.

Acceptance:

- Organizers can open a quiz from the dashboard and add questions from the frontend.
- Created questions include prompt, type, choice mode, points, optional image URL, and answer options.
- Invalid question payloads are blocked client-side where possible and surfaced clearly when rejected by the API.
- Newly created questions appear in the quiz editor without a page reload.

Verification:

- `cd frontend && npm run build`
- `cd backend && python -m pytest -q`
- Manual check: create a quiz, add one single-choice question, add one multiple-choice question, and confirm both appear in the editor.

### Phase 5: Scoring

- [x] Add deterministic scoring service for submitted answers.
- [x] Score single-choice questions.
- [x] Score multiple-choice questions.
- [x] Reject duplicate selected answer IDs in a single submission.
- [x] Persist awarded points on `question_responses`.
- [x] Return score impact from the answer submission endpoint where useful for the participant UI.
- [x] Add live scoreboard API for active sessions.
- [x] Broadcast scoreboard updates after accepted responses.
- [x] Show live scoreboard in organizer session view.
- [x] Show participant score/rank updates in participant room view.
- [x] Finalize session results when a session ends.
- [x] Detect final ranking and winner or winners.
- [x] Add tests for correct, incorrect, partial, duplicate, and repeated submissions.
- [x] Update `docs/api-contract.md` for scoring, scoreboard, and final result response shapes.

Acceptance:

- Correct answers award points deterministically.
- Duplicate answer IDs and repeated submissions are rejected.
- Scoreboard updates after responses.
- Finished session stores final results.

Verification:

- `cd backend && python -m pytest -q`
- `cd frontend && npm run build`
- Manual check: run a session with two participants, submit different answers, and confirm the live and final rankings match expected points.

### Phase 6: Personal Accounts

- [x] Add participant quiz history API.
- [x] Add organizer conducted quiz history API.
- [x] Add session result detail API.
- [x] Add dashboard sections for participant history and organizer history.
- [x] Add session result detail page with scores, ranks, winners, dates, and participant count.
- [x] Add authorization tests so users can only see their own histories or sessions they organized.
- [x] Update `docs/api-contract.md` with history and result endpoints.

Acceptance:

- Participants can see played quizzes, scores, ranks, and dates.
- Organizers can see conducted sessions, participant count, winners, and dates.
- Session result details are available only to authorized users.

Verification:

- `cd backend && python -m pytest -q`
- `cd frontend && npm run build`
- Manual check: log in as participant and organizer accounts and confirm each dashboard shows the correct historical records.

### Phase 7: Hardening

- [ ] Define and apply a consistent API error schema.
- [ ] Add negative API tests for validation, authorization, and conflict errors.
- [ ] Review and tighten CORS configuration.
- [ ] Validate upload and image URLs.
- [ ] Rate-limit sensitive endpoints.
- [ ] Set production-safe Docker defaults.
- [ ] Add CI test command for backend tests and frontend build.
- [ ] Document security-sensitive defaults and required environment variables.
- [ ] Confirm clean checkout setup works from dependency install through test/build commands.

Acceptance:

- Negative API tests pass.
- Security-sensitive defaults are documented.
- Project can be built and tested from clean checkout.

Verification:

- `cd backend && python -m pytest -q`
- `cd frontend && npm run build`
- `docker compose config`
- CI runs the same backend test and frontend build commands documented in this repo.
