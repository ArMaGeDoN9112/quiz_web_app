from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.security import verify_password
from app.db.session import get_db_session
from app.main import create_app
from app.models import User, UserRole


class FakeScalarResult:
    def __init__(self, user: User | None) -> None:
        self.user = user

    def scalar_one_or_none(self) -> User | None:
        return self.user


class FakeSession:
    def __init__(self, existing_user: User | None = None) -> None:
        self.existing_user = existing_user
        self.added_user: User | None = None
        self.committed = False

    async def execute(self, statement: object) -> FakeScalarResult:
        return FakeScalarResult(self.existing_user)

    def add(self, user: User) -> None:
        self.added_user = user

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass

    async def refresh(self, user: User) -> None:
        user.id = uuid4()
        user.created_at = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
        user.updated_at = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)


def _client_with_session(fake_session: FakeSession) -> TestClient:
    app = create_app()

    async def override_get_db_session():
        yield fake_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app)


def test_register_participant_creates_user_with_hashed_password() -> None:
    fake_session = FakeSession()
    client = _client_with_session(fake_session)

    response = client.post(
        "/auth/register",
        json={
            "email": "Participant@Example.com",
            "password": "correct horse battery staple",
            "role": "participant",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"])
    assert body["email"] == "participant@example.com"
    assert body["role"] == "participant"
    assert "password" not in body
    assert "password_hash" not in body
    assert fake_session.added_user is not None
    assert fake_session.added_user.email == "participant@example.com"
    assert fake_session.added_user.password_hash != "correct horse battery staple"
    assert verify_password(
        "correct horse battery staple", fake_session.added_user.password_hash
    )
    assert fake_session.committed is True


def test_register_organizer_creates_user_with_role() -> None:
    fake_session = FakeSession()
    client = _client_with_session(fake_session)

    response = client.post(
        "/auth/register",
        json={
            "email": "organizer@example.com",
            "password": "correct horse battery staple",
            "role": "organizer",
        },
    )

    assert response.status_code == 201
    assert response.json()["role"] == "organizer"
    assert fake_session.added_user is not None
    assert fake_session.added_user.role is UserRole.ORGANIZER


def test_register_rejects_duplicate_email() -> None:
    existing_user = User(
        email="taken@example.com",
        password_hash="already-hashed",
        role=UserRole.PARTICIPANT,
    )
    fake_session = FakeSession(existing_user=existing_user)
    client = _client_with_session(fake_session)

    response = client.post(
        "/auth/register",
        json={
            "email": "taken@example.com",
            "password": "correct horse battery staple",
            "role": "participant",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered"}
    assert fake_session.added_user is None
