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

See phase plan in original README sections for roadmap.
