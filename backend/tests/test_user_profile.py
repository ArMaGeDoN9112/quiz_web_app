from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.session import get_db_session
from app.main import create_app
from app.models import User, UserRole


class FakeScalarResult:
    def __init__(self, user: User) -> None:
        self.user = user

    def scalar_one_or_none(self) -> User:
        return self.user


class FakeSession:
    def __init__(self, user: User) -> None:
        self.user = user
        self.committed = False

    async def execute(self, statement: object) -> FakeScalarResult:
        return FakeScalarResult(self.user)

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, user: User) -> None:
        user.updated_at = datetime(2026, 7, 13, 16, 0, tzinfo=UTC)


def _user() -> User:
    user = User(
        email="participant@example.com",
        password_hash="hash",
        role=UserRole.PARTICIPANT,
    )
    user.id = uuid4()
    user.created_at = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
    user.updated_at = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
    return user


def _client(user: User) -> tuple[TestClient, FakeSession]:
    app = create_app()
    fake_session = FakeSession(user)

    async def override_get_db_session():
        yield fake_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app), fake_session


def _headers(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_participant_sets_trimmed_profile_display_name() -> None:
    user = _user()
    client, fake_session = _client(user)

    response = client.patch("/users/me", json={"display_name": "  Ada Lovelace  "}, headers=_headers(user))

    assert response.status_code == 200
    assert response.json()["display_name"] == "Ada Lovelace"
    assert user.display_name == "Ada Lovelace"
    assert fake_session.committed is True


def test_profile_rejects_blank_display_name() -> None:
    user = _user()
    client, _ = _client(user)

    response = client.patch("/users/me", json={"display_name": "   "}, headers=_headers(user))

    assert response.status_code == 422
