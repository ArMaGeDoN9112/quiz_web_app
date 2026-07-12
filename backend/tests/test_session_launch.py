import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.security import create_access_token
from app.db.session import get_db_session
from app.main import create_app
from app.models import Quiz, QuizSession, QuizStatus, SessionStatus, User, UserRole
from app.services.session import RoomCodeConflictError, launch_session


DEFAULT_SETTINGS = {
    "time_limit_seconds": 30,
    "shuffle_questions": False,
    "shuffle_answers": False,
    "show_correct_answers": True,
    "scoring_mode": "standard",
}


class FakeScalarResult:
    def __init__(self, value: object | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object | None:
        return self.value


class FakeSession:
    def __init__(
        self,
        results: list[object | None],
        commit_errors: list[Exception | None] | None = None,
    ) -> None:
        self.results = results
        self.commit_errors = commit_errors or []
        self.statements: list[object] = []
        self.added_sessions: list[QuizSession] = []
        self.committed = False
        self.rolled_back = False

    async def execute(self, statement: object) -> FakeScalarResult:
        self.statements.append(statement)
        return FakeScalarResult(self.results.pop(0))

    def add(self, obj: object) -> None:
        if isinstance(obj, QuizSession):
            self.added_sessions.append(obj)

    async def commit(self) -> None:
        if self.commit_errors:
            error = self.commit_errors.pop(0)
            if error is not None:
                raise error
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def refresh(self, obj: object) -> None:
        if isinstance(obj, QuizSession):
            obj.id = uuid4()
            obj.created_at = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
            obj.updated_at = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)


class ConstraintError(Exception):
    def __init__(self, constraint_name: str) -> None:
        super().__init__(constraint_name)
        self.constraint_name = constraint_name


def _integrity_error(constraint_name: str) -> IntegrityError:
    return IntegrityError("insert session", {}, ConstraintError(constraint_name))


def _user(email: str, role: UserRole = UserRole.ORGANIZER) -> User:
    user = User(email=email, password_hash="hashed-password", role=role)
    user.id = uuid4()
    user.created_at = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    user.updated_at = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    return user


def _quiz(owner_id: UUID) -> Quiz:
    quiz = Quiz(
        owner_id=owner_id,
        title="Science Bowl",
        description="Round one",
        status=QuizStatus.PUBLISHED,
        settings=dict(DEFAULT_SETTINGS),
    )
    quiz.id = uuid4()
    quiz.created_at = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    quiz.updated_at = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    return quiz


def _client_with_session(fake_session: FakeSession) -> TestClient:
    app = create_app()

    async def override_get_db_session():
        yield fake_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app)


def _auth_header(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_organizer_launches_session_for_own_quiz() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    fake_session = FakeSession(results=[organizer, quiz])
    client = _client_with_session(fake_session)

    response = client.post(
        "/sessions",
        json={"quiz_id": str(quiz.id)},
        headers=_auth_header(organizer),
    )

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"])
    assert body["quiz_id"] == str(quiz.id)
    assert body["organizer_id"] == str(organizer.id)
    assert len(body["room_code"]) == 6
    assert body["room_code"].isalnum()
    assert body["status"] == "waiting"
    assert fake_session.added_sessions[0].quiz_id == quiz.id
    assert fake_session.added_sessions[0].organizer_id == organizer.id
    assert fake_session.committed is True


def test_launch_session_requires_organizer_role() -> None:
    participant = _user("participant@example.com", role=UserRole.PARTICIPANT)
    fake_session = FakeSession(results=[participant])
    client = _client_with_session(fake_session)

    response = client.post(
        "/sessions",
        json={"quiz_id": str(uuid4())},
        headers=_auth_header(participant),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Organizer role required"}
    assert fake_session.added_sessions == []


def test_launch_session_rejects_quiz_not_owned_by_organizer() -> None:
    organizer = _user("organizer@example.com")
    quiz_id = uuid4()
    fake_session = FakeSession(results=[organizer, None])
    client = _client_with_session(fake_session)

    response = client.post(
        "/sessions",
        json={"quiz_id": str(quiz_id)},
        headers=_auth_header(organizer),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Quiz not found"}
    assert fake_session.added_sessions == []
    assert fake_session.statements[1].compile().params == {
        "id_1": quiz_id,
        "owner_id_1": organizer.id,
    }


def test_launch_session_retries_duplicate_room_code() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    fake_session = FakeSession(
        results=[quiz],
        commit_errors=[
            _integrity_error("uq_sessions_room_code"),
            None,
        ],
    )
    room_codes = iter(["ABC123", "XYZ789"])

    launched = asyncio.run(
        launch_session(
            fake_session,
            organizer,
            quiz.id,
            room_code_factory=lambda: next(room_codes),
        )
    )

    assert launched.room_code == "XYZ789"
    assert [session.room_code for session in fake_session.added_sessions] == [
        "ABC123",
        "XYZ789",
    ]
    assert fake_session.rolled_back is True
    assert fake_session.committed is True


def test_launch_session_raises_room_code_conflict_after_all_attempts_fail() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    fake_session = FakeSession(
        results=[quiz],
        commit_errors=[
            _integrity_error("uq_sessions_room_code"),
            _integrity_error("uq_sessions_room_code"),
            _integrity_error("uq_sessions_room_code"),
            _integrity_error("uq_sessions_room_code"),
            _integrity_error("uq_sessions_room_code"),
        ],
    )
    room_codes = iter(["AAA111", "BBB222", "CCC333", "DDD444", "EEE555"])

    try:
        asyncio.run(
            launch_session(
                fake_session,
                organizer,
                quiz.id,
                room_code_factory=lambda: next(room_codes),
            )
        )
    except RoomCodeConflictError:
        pass
    else:
        raise AssertionError("Expected RoomCodeConflictError")

    assert [session.room_code for session in fake_session.added_sessions] == [
        "AAA111",
        "BBB222",
        "CCC333",
        "DDD444",
        "EEE555",
    ]
    assert fake_session.rolled_back is True
    assert fake_session.committed is False


def test_launch_session_does_not_mask_non_room_code_integrity_error() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    fake_session = FakeSession(
        results=[quiz],
        commit_errors=[_integrity_error("fk_sessions_quiz_id_quizzes")],
    )

    try:
        asyncio.run(
            launch_session(
                fake_session,
                organizer,
                quiz.id,
                room_code_factory=lambda: "ABC123",
            )
        )
    except IntegrityError as error:
        assert "fk_sessions_quiz_id_quizzes" in str(error.orig)
    else:
        raise AssertionError("Expected IntegrityError")

    assert len(fake_session.added_sessions) == 1
    assert fake_session.rolled_back is True
    assert fake_session.committed is False


def test_launch_session_endpoint_maps_room_code_conflict_to_409() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    fake_session = FakeSession(
        results=[organizer, quiz],
        commit_errors=[
            _integrity_error("uq_sessions_room_code"),
            _integrity_error("uq_sessions_room_code"),
            _integrity_error("uq_sessions_room_code"),
            _integrity_error("uq_sessions_room_code"),
            _integrity_error("uq_sessions_room_code"),
        ],
    )
    client = _client_with_session(fake_session)

    response = client.post(
        "/sessions",
        json={"quiz_id": str(quiz.id)},
        headers=_auth_header(organizer),
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Room code conflict; retry request"}
