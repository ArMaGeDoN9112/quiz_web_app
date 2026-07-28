import asyncio
from unittest.mock import ANY
from uuid import uuid4

import pytest

from app.models import User, UserRole
from app.services import session_commands


def _user(role: UserRole) -> User:
    user = User(
        email=f"{role.value}@example.com",
        password_hash="hashed-password",
        role=role,
    )
    user.id = uuid4()
    return user


def test_dispatch_start_question_validates_and_forwards_command(monkeypatch) -> None:
    organizer = _user(UserRole.ORGANIZER)
    session_id = uuid4()
    question_id = uuid4()
    received: list[tuple[object, object, object, object]] = []

    async def fake_start_question(
        session: object,
        user: User,
        target_session_id: object,
        target_question_id: object,
        *,
        duration_seconds: int | None,
    ) -> None:
        received.append(
            (session, user, target_session_id, (target_question_id, duration_seconds))
        )

    monkeypatch.setattr(session_commands, "start_question", fake_start_question)

    command = asyncio.run(
        session_commands.dispatch_session_command(
            object(),
            organizer,
            session_id,
            {
                "type": "question.start",
                "request_id": str(uuid4()),
                "question_id": str(question_id),
                "duration_seconds": 15,
            },
        )
    )

    assert command.question_id == question_id
    assert received == [(ANY, organizer, session_id, (question_id, 15))]


def test_dispatch_submit_answer_requires_participant(monkeypatch) -> None:
    organizer = _user(UserRole.ORGANIZER)

    async def unexpected_submit_answer(*args, **kwargs) -> None:
        raise AssertionError("submit_answer must not be called")

    monkeypatch.setattr(session_commands, "submit_answer", unexpected_submit_answer)

    with pytest.raises(PermissionError, match="Participant role required"):
        asyncio.run(
            session_commands.dispatch_session_command(
                object(),
                organizer,
                uuid4(),
                {
                    "type": "answer.submit",
                    "request_id": str(uuid4()),
                    "question_id": str(uuid4()),
                    "selected_answer_ids": [str(uuid4())],
                },
            )
        )


def test_dispatch_submit_answer_forwards_participant_command(monkeypatch) -> None:
    participant = _user(UserRole.PARTICIPANT)
    session_id = uuid4()
    question_id = uuid4()
    answer_id = uuid4()
    received: list[tuple[object, ...]] = []

    async def fake_submit_answer(*args: object) -> None:
        received.append(args)

    monkeypatch.setattr(session_commands, "submit_answer", fake_submit_answer)

    command = asyncio.run(
        session_commands.dispatch_session_command(
            object(),
            participant,
            session_id,
            {
                "type": "answer.submit",
                "request_id": str(uuid4()),
                "question_id": str(question_id),
                "selected_answer_ids": [str(answer_id)],
                "text_answer": "  explanation  ",
            },
        )
    )

    assert command.text_answer == "explanation"
    assert received == [
        (ANY, participant, session_id, question_id, [answer_id], "explanation")
    ]


def test_dispatch_end_session_forwards_organizer_command(monkeypatch) -> None:
    organizer = _user(UserRole.ORGANIZER)
    session_id = uuid4()
    received: list[tuple[object, User, object]] = []

    async def fake_end_session(
        session: object,
        user: User,
        target_session_id: object,
    ) -> None:
        received.append((session, user, target_session_id))

    monkeypatch.setattr(session_commands, "end_session", fake_end_session)

    command = asyncio.run(
        session_commands.dispatch_session_command(
            object(),
            organizer,
            session_id,
            {"type": "session.end", "request_id": str(uuid4())},
        )
    )

    assert command.type == "session.end"
    assert received == [(ANY, organizer, session_id)]


def test_dispatch_rejects_unsupported_command() -> None:
    with pytest.raises(ValueError, match="Unsupported command"):
        asyncio.run(
            session_commands.dispatch_session_command(
                object(),
                _user(UserRole.ORGANIZER),
                uuid4(),
                {"type": "session.pause", "request_id": str(uuid4())},
            )
        )
