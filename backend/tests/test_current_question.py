from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.session import get_db_session
from app.main import create_app
from app.models import (
    Answer,
    ChoiceMode,
    Question,
    QuestionEvent,
    QuestionEventStatus,
    QuestionType,
    QuizSession,
    SessionParticipant,
    SessionStatus,
    User,
    UserRole,
)


class FakeScalarResult:
    def __init__(self, value: object | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object | None:
        return self.value


class FakeSession:
    def __init__(self, results: list[object | None]) -> None:
        self.results = results

    async def execute(self, statement: object) -> FakeScalarResult:
        return FakeScalarResult(self.results.pop(0))


def _user(email: str, role: UserRole) -> User:
    user = User(email=email, password_hash="hash", role=role)
    user.id = uuid4()
    user.created_at = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
    user.updated_at = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
    return user


def _session(organizer: User) -> QuizSession:
    quiz_session = QuizSession(
        quiz_id=uuid4(), organizer_id=organizer.id, room_code="ABC123", status=SessionStatus.ACTIVE
    )
    quiz_session.id = uuid4()
    quiz_session.created_at = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
    quiz_session.updated_at = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
    return quiz_session


def _participant(quiz_session: QuizSession, user: User) -> SessionParticipant:
    participant = SessionParticipant(session_id=quiz_session.id, user_id=user.id, display_name="Ada")
    participant.id = uuid4()
    participant.joined_at = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
    return participant


def _question(quiz_session: QuizSession) -> Question:
    question = Question(
        quiz_id=quiz_session.quiz_id,
        type=QuestionType.TEXT,
        choice_mode=ChoiceMode.SINGLE,
        text="Capital of France?",
        image_url=None,
        points=5,
        position=1,
        answers=[
            Answer(text="Paris", is_correct=True, position=1),
            Answer(text="Rome", is_correct=False, position=2),
        ],
    )
    question.id = uuid4()
    for answer in question.answers:
        answer.id = uuid4()
    return question


def _event(quiz_session: QuizSession, question: Question) -> QuestionEvent:
    event = QuestionEvent(
        session_id=quiz_session.id,
        question_id=question.id,
        status=QuestionEventStatus.ACTIVE,
        started_at=datetime(2026, 7, 13, 12, 0, tzinfo=UTC),
        ended_at=datetime(2026, 7, 13, 12, 0, tzinfo=UTC) + timedelta(seconds=30),
    )
    event.id = uuid4()
    return event


def _client(fake_session: FakeSession) -> TestClient:
    app = create_app()

    async def override_get_db_session():
        yield fake_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app)


def _headers(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_joined_participant_gets_active_question_without_correct_answers() -> None:
    organizer = _user("organizer@example.com", UserRole.ORGANIZER)
    participant_user = _user("participant@example.com", UserRole.PARTICIPANT)
    quiz_session = _session(organizer)
    participant = _participant(quiz_session, participant_user)
    question = _question(quiz_session)
    event = _event(quiz_session, question)
    client = _client(FakeSession([participant_user, quiz_session, participant, event, question]))

    response = client.get(f"/sessions/{quiz_session.id}/questions/current", headers=_headers(participant_user))

    assert response.status_code == 200
    body = response.json()
    assert body["event_id"] == str(event.id)
    assert body["text"] == "Capital of France?"
    assert body["answers"] == [
        {"id": str(question.answers[0].id), "text": "Paris", "position": 1},
        {"id": str(question.answers[1].id), "text": "Rome", "position": 2},
    ]
    assert "is_correct" not in str(body)


def test_current_question_rejects_user_who_did_not_join() -> None:
    organizer = _user("organizer@example.com", UserRole.ORGANIZER)
    outsider = _user("outsider@example.com", UserRole.PARTICIPANT)
    quiz_session = _session(organizer)
    client = _client(FakeSession([outsider, quiz_session, None]))

    response = client.get(f"/sessions/{quiz_session.id}/questions/current", headers=_headers(outsider))

    assert response.status_code == 403
    assert response.json() == {"detail": "Session access denied"}
