import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.session import get_db_session
from app.main import create_app
from app.models import QuizSession, SessionParticipant, SessionStatus, User, UserRole
from app.services.session import get_session_context


class FakeScalarResult:
    def __init__(self, value: object | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object | None:
        return self.value


class FakeSession:
    def __init__(self, results: list[object | None]) -> None:
        self.results = results

    async def execute(self, _: object) -> FakeScalarResult:
        return FakeScalarResult(self.results.pop(0))


def _user(role: UserRole) -> User:
    user = User(email=f"{role.value}@example.com", password_hash="hash", role=role)
    user.id = uuid4()
    return user


def _quiz_session(organizer_id: object) -> QuizSession:
    quiz_session = QuizSession(
        quiz_id=uuid4(),
        organizer_id=organizer_id,
        room_code="ABC123",
        status=SessionStatus.ACTIVE,
    )
    quiz_session.id = uuid4()
    quiz_session.created_at = datetime(2026, 7, 16, tzinfo=UTC)
    quiz_session.updated_at = datetime(2026, 7, 16, tzinfo=UTC)
    return quiz_session


def test_session_context_returns_session_without_participant_for_organizer() -> None:
    organizer = _user(UserRole.ORGANIZER)
    quiz_session = _quiz_session(organizer.id)

    context = asyncio.run(get_session_context(FakeSession([quiz_session]), organizer, quiz_session.id))

    assert context.session is quiz_session
    assert context.participant is None


def test_session_context_returns_joined_participant() -> None:
    organizer = _user(UserRole.ORGANIZER)
    participant_user = _user(UserRole.PARTICIPANT)
    quiz_session = _quiz_session(organizer.id)
    participant = SessionParticipant(
        session_id=quiz_session.id,
        user_id=participant_user.id,
        display_name="Ada",
    )
    participant.id = uuid4()

    context = asyncio.run(
        get_session_context(FakeSession([quiz_session, participant]), participant_user, quiz_session.id)
    )

    assert context.session is quiz_session
    assert context.participant is participant


def test_session_context_endpoint_restores_participant_membership() -> None:
    organizer = _user(UserRole.ORGANIZER)
    participant_user = _user(UserRole.PARTICIPANT)
    quiz_session = _quiz_session(organizer.id)
    participant = SessionParticipant(
        session_id=quiz_session.id,
        user_id=participant_user.id,
        display_name="Ada",
    )
    participant.id = uuid4()
    participant.joined_at = datetime(2026, 7, 16, tzinfo=UTC)
    fake_session = FakeSession([participant_user, quiz_session, participant])
    app = create_app()

    async def override_get_db_session():
        yield fake_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    token = create_access_token(subject=str(participant_user.id), role=participant_user.role.value)

    response = TestClient(app).get(
        f"/sessions/{quiz_session.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["session"]["id"] == str(quiz_session.id)
    assert response.json()["participant"]["id"] == str(participant.id)
