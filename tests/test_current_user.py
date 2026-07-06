from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import Depends
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.session import get_db_session
from app.main import create_app
from app.models import User, UserRole


class FakeScalarResult:
    def __init__(self, user: User | None) -> None:
        self.user = user

    def scalar_one_or_none(self) -> User | None:
        return self.user


class FakeSession:
    def __init__(self, user: User | None = None) -> None:
        self.user = user
        self.statement: object | None = None

    async def execute(self, statement: object) -> FakeScalarResult:
        self.statement = statement
        return FakeScalarResult(self.user)


def _user(email: str, role: UserRole = UserRole.PARTICIPANT) -> User:
    user = User(
        email=email,
        password_hash="hashed-password",
        role=role,
    )
    user.id = uuid4()
    user.created_at = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
    user.updated_at = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
    return user


def _client_with_session(fake_session: FakeSession) -> TestClient:
    app = create_app()

    async def override_get_db_session():
        yield fake_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app)


def _bearer_token(user: User) -> str:
    return create_access_token(subject=str(user.id), role=user.role.value)


def test_users_me_returns_authenticated_user() -> None:
    user = _user("participant@example.com")
    fake_session = FakeSession(user=user)
    client = _client_with_session(fake_session)

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {_bearer_token(user)}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert UUID(body["id"]) == user.id
    assert body["email"] == "participant@example.com"
    assert body["role"] == "participant"
    assert "password_hash" not in body
    assert fake_session.statement is not None
    assert fake_session.statement.compile().params == {"id_1": user.id}


def test_users_me_rejects_missing_token() -> None:
    client = _client_with_session(FakeSession())

    response = client.get("/users/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing bearer token"}


def test_users_me_rejects_invalid_token() -> None:
    client = _client_with_session(FakeSession())

    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid bearer token"}


def test_organizer_guard_rejects_wrong_role() -> None:
    from app.api.dependencies.auth import require_organizer

    user = _user("participant@example.com", role=UserRole.PARTICIPANT)
    app = create_app()

    async def override_get_db_session():
        yield FakeSession(user=user)

    @app.get("/organizer-only")
    async def organizer_only(current_user: User = Depends(require_organizer)):
        return {"id": str(current_user.id)}

    app.dependency_overrides[get_db_session] = override_get_db_session
    client = TestClient(app)

    response = client.get(
        "/organizer-only",
        headers={"Authorization": f"Bearer {_bearer_token(user)}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Organizer role required"}


def test_organizer_guard_allows_organizer() -> None:
    from app.api.dependencies.auth import require_organizer

    user = _user("organizer@example.com", role=UserRole.ORGANIZER)
    app = create_app()

    async def override_get_db_session():
        yield FakeSession(user=user)

    @app.get("/organizer-only")
    async def organizer_only(current_user: User = Depends(require_organizer)):
        return {"id": str(current_user.id)}

    app.dependency_overrides[get_db_session] = override_get_db_session
    client = TestClient(app)

    response = client.get(
        "/organizer-only",
        headers={"Authorization": f"Bearer {_bearer_token(user)}"},
    )

    assert response.status_code == 200
    assert response.json() == {"id": str(user.id)}
