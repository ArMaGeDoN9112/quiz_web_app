import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.session import get_db_session
from app.main import create_app
from app.models import QuizSession, SessionParticipant, SessionStatus, User, UserRole
from app.services.session import (
    DuplicateSessionParticipantError,
    SessionNotJoinableError,
    join_session,
)


class FakeScalarResult:
    def __init__(self, value: object | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object | None:
        return self.value


class FakeSession:
    def __init__(self, results: list[object | None]) -> None:
        self.results = results
        self.statements: list[object] = []
        self.added_participants: list[SessionParticipant] = []
        self.committed = False

    async def execute(self, statement: object) -> FakeScalarResult:
        self.statements.append(statement)
        return FakeScalarResult(self.results.pop(0))

    def add(self, obj: object) -> None:
        if isinstance(obj, SessionParticipant):
            self.added_participants.append(obj)

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass

    async def refresh(self, obj: object) -> None:
        if isinstance(obj, SessionParticipant):
            obj.id = uuid4()
            obj.joined_at = datetime(2026, 7, 7, 13, 0, tzinfo=UTC)


def _user(email: str, role: UserRole = UserRole.PARTICIPANT) -> User:
    user = User(email=email, password_hash="hashed-password", role=role)
    user.id = uuid4()
    user.created_at = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    user.updated_at = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    return user


def _quiz_session(status: SessionStatus = SessionStatus.WAITING) -> QuizSession:
    session = QuizSession(
        quiz_id=uuid4(),
        organizer_id=uuid4(),
        room_code="ABC123",
        status=status,
    )
    session.id = uuid4()
    session.created_at = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    session.updated_at = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    return session


def _participant(quiz_session: QuizSession, user: User) -> SessionParticipant:
    participant = SessionParticipant(
        session_id=quiz_session.id,
        user_id=user.id,
        display_name="Ada",
    )
    participant.id = uuid4()
    participant.joined_at = datetime(2026, 7, 7, 12, 30, tzinfo=UTC)
    return participant


def _client_with_session(fake_session: FakeSession) -> TestClient:
    app = create_app()

    async def override_get_db_session():
        yield fake_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app)


def _auth_header(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_participant_joins_waiting_session() -> None:
    participant_user = _user("participant@example.com")
    quiz_session = _quiz_session()
    fake_session = FakeSession(results=[participant_user, quiz_session, None])
    client = _client_with_session(fake_session)

    response = client.post(
        "/sessions/join",
        json={"room_code": " abc123 ", "display_name": "Ada Lovelace"},
        headers=_auth_header(participant_user),
    )

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"])
    assert body["session_id"] == str(quiz_session.id)
    assert body["user_id"] == str(participant_user.id)
    assert body["display_name"] == "Ada Lovelace"
    assert fake_session.added_participants[0].session_id == quiz_session.id
    assert fake_session.added_participants[0].user_id == participant_user.id
    assert fake_session.committed is True


def test_join_session_rejects_ended_room() -> None:
    participant_user = _user("participant@example.com")
    ended_session = _quiz_session(SessionStatus.ENDED)
    fake_session = FakeSession(results=[ended_session])

    try:
        asyncio.run(join_session(fake_session, participant_user, "ABC123", "Ada"))
    except SessionNotJoinableError:
        pass
    else:
        raise AssertionError("Expected SessionNotJoinableError")

    assert fake_session.added_participants == []
    assert fake_session.committed is False


def test_join_session_rejects_duplicate_participant() -> None:
    participant_user = _user("participant@example.com")
    quiz_session = _quiz_session()
    existing_participant = _participant(quiz_session, participant_user)
    fake_session = FakeSession(results=[quiz_session, existing_participant])

    try:
        asyncio.run(join_session(fake_session, participant_user, "ABC123", "Ada"))
    except DuplicateSessionParticipantError:
        pass
    else:
        raise AssertionError("Expected DuplicateSessionParticipantError")

    assert fake_session.added_participants == []
    assert fake_session.committed is False


def test_join_endpoint_maps_inactive_room_to_404() -> None:
    participant_user = _user("participant@example.com")
    fake_session = FakeSession(results=[participant_user, None])
    client = _client_with_session(fake_session)

    response = client.post(
        "/sessions/join",
        json={"room_code": "MISSING", "display_name": "Ada"},
        headers=_auth_header(participant_user),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Session is not joinable"}


def test_join_endpoint_maps_duplicate_join_to_409() -> None:
    participant_user = _user("participant@example.com")
    quiz_session = _quiz_session()
    existing_participant = _participant(quiz_session, participant_user)
    fake_session = FakeSession(results=[participant_user, quiz_session, existing_participant])
    client = _client_with_session(fake_session)

    response = client.post(
        "/sessions/join",
        json={"room_code": "ABC123", "display_name": "Ada"},
        headers=_auth_header(participant_user),
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "User already joined session"}


def test_join_endpoint_requires_participant_role() -> None:
    organizer = _user("organizer@example.com", role=UserRole.ORGANIZER)
    fake_session = FakeSession(results=[organizer])
    client = _client_with_session(fake_session)

    response = client.post(
        "/sessions/join",
        json={"room_code": "ABC123", "display_name": "Ada"},
        headers=_auth_header(organizer),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Participant role required"}
    assert fake_session.added_participants == []


def test_join_endpoint_rejects_blank_display_name_after_trimming() -> None:
    participant_user = _user("participant@example.com")
    fake_session = FakeSession(results=[participant_user])
    client = _client_with_session(fake_session)

    response = client.post(
        "/sessions/join",
        json={"room_code": "ABC123", "display_name": "   "},
        headers=_auth_header(participant_user),
    )

    assert response.status_code == 422
    assert fake_session.added_participants == []
