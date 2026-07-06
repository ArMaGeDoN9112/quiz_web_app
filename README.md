# Quiz Web App Backend

Backend for web quiz app where organizers create quizzes, launch live rooms, and participants answer questions in real time.

## Stack

- Python 3.12
- FastAPI
- SQLAlchemy 2 async
- PostgreSQL
- Alembic
- Pydantic v2
- Uvicorn
- Docker Compose
- pytest

## Phase Plan

### Phase 1: Foundation

- [x] Create project scaffold.
- [x] Add FastAPI app entrypoint.
- [x] Add `/health` endpoint.
- [x] Add typed config from environment.
- [x] Add async SQLAlchemy engine/session setup.
- [x] Add Alembic configuration.
- [x] Add Dockerfile and Docker Compose for API + PostgreSQL.
- [x] Add pytest setup and smoke tests.

Acceptance:

- API boots.
- `/health` returns `{"status": "ok"}`.
- Docker Compose can run API + PostgreSQL.
- Tests cover app creation and health route.

### Phase 2: Auth

- [ ] User registration for participants and organizers.
- [ ] Password hashing.
- [ ] JWT login.
- [ ] Current-user endpoint.
- [ ] Role guards for organizer-only routes.

Acceptance:

- Users can register with unique email.
- Users can log in and receive access token.
- Protected routes reject missing/invalid token.
- Organizer-only routes reject participant users.

### Phase 3: Quiz Management

- [ ] Quiz CRUD for organizers.
- [ ] Category management.
- [ ] Quiz settings: time limits, rules, scoring.
- [ ] Text and image questions.
- [ ] Single-choice and multiple-choice answers.

Acceptance:

- Organizer can create and edit own quizzes.
- Invalid question configs are rejected.
- Participants cannot mutate quiz definitions.

### Phase 4: Live Sessions

- [ ] Launch quiz session.
- [ ] Generate unique room code.
- [ ] Join active session by room code.
- [ ] Track participant presence.
- [ ] Expose active question state.
- [ ] WebSocket endpoint for real-time quiz events.

Acceptance:

- Organizer launches room.
- Participant joins once by room code.
- Active question is visible only during its time window.
- Late answers are rejected.

### Phase 5: Scoring

- [ ] Submit answers.
- [ ] Score single-choice and multiple-choice questions.
- [ ] Reject duplicate answers.
- [ ] Live scoreboard.
- [ ] Final ranking and winner detection.

Acceptance:

- Correct answers award points deterministically.
- Scoreboard updates after responses.
- Finished session stores final results.

### Phase 6: Personal Accounts

- [ ] Participant quiz history.
- [ ] Organizer conducted quiz history.
- [ ] Session result details.

Acceptance:

- Participants can see played quizzes, scores, ranks, and dates.
- Organizers can see conducted sessions, participant count, winners, and dates.

### Phase 7: Hardening

- [ ] Consistent API error schema.
- [ ] CORS config.
- [ ] Upload/image URL validation.
- [ ] Rate-limit sensitive endpoints.
- [ ] Production Docker defaults.
- [ ] CI test command.

Acceptance:

- Negative API tests pass.
- Security-sensitive defaults are documented.
- Project can be built and tested from clean checkout.

## Target API Groups

- `POST /auth/register`
- `POST /auth/login`
- `GET /users/me`
- `GET /quizzes`
- `POST /quizzes`
- `PATCH /quizzes/{quiz_id}`
- `POST /quizzes/{quiz_id}/questions`
- `POST /sessions`
- `POST /sessions/join`
- `POST /sessions/{session_id}/answer`
- `GET /sessions/{session_id}/scoreboard`
- `GET /history/participant`
- `GET /history/organizer`
- `WS /ws/sessions/{room_code}`

## Local Development

Copy `.env.example` to `.env`, then run:

```bash
docker compose up --build
```

API:

- `GET http://localhost:8000/health`
- OpenAPI docs: `http://localhost:8000/docs`

Run tests locally:

```bash
python -m pytest
```

Run migrations:

```bash
alembic upgrade head
```

