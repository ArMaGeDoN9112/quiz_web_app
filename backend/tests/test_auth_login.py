from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.security import hash_password, verify_access_token
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


def _client_with_session(fake_session: FakeSession) -> TestClient:
    app = create_app()

    async def override_get_db_session():
        yield fake_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app)


def _user(email: str, password: str, role: UserRole = UserRole.PARTICIPANT) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    user.id = uuid4()
    user.created_at = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
    user.updated_at = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
    return user


def test_login_returns_bearer_token_for_valid_credentials() -> None:
    user = _user("participant@example.com", "correct horse battery staple")
    fake_session = FakeSession(user=user)
    client = _client_with_session(fake_session)

    response = client.post(
        "/auth/login",
        json={
            "email": "Participant@Example.com",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["access_token"]
    payload = verify_access_token(body["access_token"])
    assert payload is not None
    assert UUID(payload["sub"]) == user.id
    assert payload["role"] == "participant"
    assert fake_session.statement is not None
    assert fake_session.statement.compile().params == {
        "email_1": "participant@example.com"
    }


def test_login_rejects_invalid_password() -> None:
    user = _user("participant@example.com", "correct horse battery staple")
    client = _client_with_session(FakeSession(user=user))

    response = client.post(
        "/auth/login",
        json={
            "email": "participant@example.com",
            "password": "wrong horse battery staple",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


def test_login_rejects_unknown_email() -> None:
    client = _client_with_session(FakeSession(user=None))

    response = client.post(
        "/auth/login",
        json={
            "email": "missing@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}
