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
- `POST /sessions`, `POST /sessions/join`, `GET /sessions/{id}`
- `POST /sessions/{id}/answer`
- `GET /sessions/{id}/scoreboard`, `POST /sessions/{id}/end`

Automatic playback runs in backend process: after host starts first question,
server advances timed questions and ends session after last question. PostgreSQL
row locking prevents duplicate transitions when multiple API processes run.
