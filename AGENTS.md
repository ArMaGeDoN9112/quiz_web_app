# Agent Instructions

## Project

Backend for live quiz web app.

Stack:

- Python 3.12
- FastAPI
- SQLAlchemy 2 async
- PostgreSQL
- Alembic
- Pydantic v2
- Uvicorn
- Docker Compose
- pytest

## Repo-Local Skills

Prefer repo-local skills in `.agents/skills/` before global skills.

Use these when relevant:

- `.agents/skills/using-agent-skills/SKILL.md` for skill selection.
- `.agents/skills/planning-and-task-breakdown/SKILL.md` for plans/tasks.
- `.agents/skills/spec-driven-development/SKILL.md` for new feature specs.
- `.agents/skills/incremental-implementation/SKILL.md` for multi-file work.
- `.agents/skills/test-driven-development/SKILL.md` for behavior changes.
- `.agents/skills/api-and-interface-design/SKILL.md` for API contract work.
- `.agents/skills/security-and-hardening/SKILL.md` for auth, sessions, user input.
- `.agents/skills/code-review-and-quality/SKILL.md` for review before completion.
- `.agents/skills/cavecrew/SKILL.md` for compressed subagent delegation.
- `.agents/skills/caveman/SKILL.md` when user asks for caveman style.

If a skill is named in a task file, read it before editing code.

## Architecture Rules

Keep layers separated:

- `app/api/routes/`: HTTP/WebSocket route handlers only.
- `app/schemas/`: Pydantic request/response models.
- `app/models/`: SQLAlchemy ORM models.
- `app/services/`: business logic.
- `app/repositories/`: database query helpers when queries become non-trivial.
- `app/core/`: config, security, app-wide primitives.
- `app/db/`: engine/session/base metadata.
- `tests/`: pytest tests.

Routes should validate input, call services, and return schemas. Do not put business workflows directly in route handlers.

## Implementation Rules

- Use async SQLAlchemy APIs.
- Use Pydantic v2 syntax.
- Add tests for every behavior change.
- Add Alembic migration for schema changes.
- Keep changes scoped to current task.
- Do not refactor unrelated files.
- Do not commit secrets or real credentials.
- Do not skip tests to make suite pass.

## Commands

Install deps:

```bash
python -m pip install -r requirements-dev.txt
```

Run tests:

```bash
python -m pytest -q
```

Compile check:

```bash
python -m py_compile app/main.py
```

Run app:

```bash
uvicorn app.main:app --reload
```

Run Docker:

```bash
docker compose up --build
```

Run migrations:

```bash
alembic upgrade head
```

## Definition of Done

- Tests added or updated.
- `python -m pytest -q` passes.
- Relevant docs/tasks updated.
- Schema changes have Alembic migration.
- API behavior documented in `docs/api-contract.md` when public contract changes.

