import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.session import get_db_session
from app.main import create_app
from app.models import Quiz, QuizStatus, User, UserRole
from app.services.quiz import list_quizzes


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


class FakeScalars:
    def __init__(self, values: list[object]) -> None:
        self.values = values

    def all(self) -> list[object]:
        return self.values


class FakeListResult:
    def __init__(self, values: list[object]) -> None:
        self.values = values

    def scalars(self) -> FakeScalars:
        return FakeScalars(self.values)


class FakeSession:
    def __init__(self, results: list[object | list[object] | None]) -> None:
        self.results = results
        self.statements: list[object] = []
        self.added_quiz: Quiz | None = None
        self.deleted_quiz: Quiz | None = None
        self.committed = False
        self.rolled_back = False

    async def execute(self, statement: object) -> FakeScalarResult | FakeListResult:
        self.statements.append(statement)
        result = self.results.pop(0)
        if isinstance(result, list):
            return FakeListResult(result)
        return FakeScalarResult(result)

    def add(self, quiz: Quiz) -> None:
        self.added_quiz = quiz

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def refresh(self, quiz: Quiz) -> None:
        quiz.id = uuid4()
        quiz.created_at = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
        quiz.updated_at = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)

    async def delete(self, quiz: Quiz) -> None:
        self.deleted_quiz = quiz


def _user(email: str, role: UserRole = UserRole.ORGANIZER) -> User:
    user = User(email=email, password_hash="hashed-password", role=role)
    user.id = uuid4()
    user.created_at = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
    user.updated_at = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
    return user


def _quiz(owner_id: UUID, title: str = "Science Bowl") -> Quiz:
    quiz = Quiz(
        owner_id=owner_id,
        title=title,
        description="Round one",
        status=QuizStatus.DRAFT,
        settings=dict(DEFAULT_SETTINGS),
    )
    quiz.id = uuid4()
    quiz.created_at = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
    quiz.updated_at = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
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


def test_organizer_creates_quiz_owned_by_self() -> None:
    organizer = _user("organizer@example.com")
    fake_session = FakeSession(results=[organizer])
    client = _client_with_session(fake_session)

    response = client.post(
        "/quizzes",
        json={"title": "  Science Bowl  ", "description": "Round one"},
        headers=_auth_header(organizer),
    )

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"])
    assert body["owner_id"] == str(organizer.id)
    assert body["title"] == "Science Bowl"
    assert body["description"] == "Round one"
    assert body["status"] == "draft"
    assert body["settings"] == DEFAULT_SETTINGS
    assert fake_session.added_quiz is not None
    assert fake_session.added_quiz.owner_id == organizer.id
    assert fake_session.added_quiz.title == "Science Bowl"
    assert fake_session.added_quiz.settings == DEFAULT_SETTINGS
    assert fake_session.committed is True


def test_organizer_lists_only_own_quizzes() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    fake_session = FakeSession(results=[organizer, [quiz]])
    client = _client_with_session(fake_session)

    response = client.get("/quizzes", headers=_auth_header(organizer))

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(quiz.id),
            "owner_id": str(organizer.id),
            "title": "Science Bowl",
            "description": "Round one",
            "status": "draft",
            "settings": DEFAULT_SETTINGS,
            "created_at": "2026-07-06T12:00:00Z",
            "updated_at": "2026-07-06T12:00:00Z",
        }
    ]
    assert len(fake_session.statements) == 2
    assert fake_session.statements[1].compile().params == {"owner_id_1": organizer.id}


def test_list_quizzes_service_returns_owner_quizzes_in_query_order() -> None:
    organizer = _user("organizer@example.com")
    first_quiz = _quiz(organizer.id, title="First Quiz")
    second_quiz = _quiz(organizer.id, title="Second Quiz")
    fake_session = FakeSession(results=[[first_quiz, second_quiz]])

    quizzes = asyncio.run(list_quizzes(fake_session, organizer))

    assert quizzes == [first_quiz, second_quiz]
    assert fake_session.statements[0].compile().params == {"owner_id_1": organizer.id}


def test_organizer_gets_own_quiz() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    fake_session = FakeSession(results=[organizer, quiz])
    client = _client_with_session(fake_session)

    response = client.get(f"/quizzes/{quiz.id}", headers=_auth_header(organizer))

    assert response.status_code == 200
    assert response.json()["id"] == str(quiz.id)
    assert response.json()["owner_id"] == str(organizer.id)
    assert response.json()["settings"] == DEFAULT_SETTINGS
    assert fake_session.statements[1].compile().params == {
        "id_1": quiz.id,
        "owner_id_1": organizer.id,
    }


def test_non_owner_cannot_get_quiz() -> None:
    organizer = _user("organizer@example.com")
    quiz_id = uuid4()
    fake_session = FakeSession(results=[organizer, None])
    client = _client_with_session(fake_session)

    response = client.get(f"/quizzes/{quiz_id}", headers=_auth_header(organizer))

    assert response.status_code == 404
    assert response.json() == {"detail": "Quiz not found"}
    assert fake_session.statements[1].compile().params == {
        "id_1": quiz_id,
        "owner_id_1": organizer.id,
    }


def test_organizer_updates_own_quiz() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    fake_session = FakeSession(results=[organizer, quiz])
    client = _client_with_session(fake_session)

    response = client.patch(
        f"/quizzes/{quiz.id}",
        json={"title": "Final Round", "status": "published"},
        headers=_auth_header(organizer),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Final Round"
    assert body["description"] == "Round one"
    assert body["status"] == "published"
    assert quiz.title == "Final Round"
    assert quiz.status is QuizStatus.PUBLISHED
    assert fake_session.committed is True


def test_organizer_creates_quiz_with_settings() -> None:
    organizer = _user("organizer@example.com")
    fake_session = FakeSession(results=[organizer])
    client = _client_with_session(fake_session)

    response = client.post(
        "/quizzes",
        json={
            "title": "Science Bowl",
            "settings": {
                "time_limit_seconds": 45,
                "shuffle_questions": True,
                "scoring_mode": "speed_bonus",
            },
        },
        headers=_auth_header(organizer),
    )

    expected_settings = {
        **DEFAULT_SETTINGS,
        "time_limit_seconds": 45,
        "shuffle_questions": True,
        "scoring_mode": "speed_bonus",
    }
    assert response.status_code == 201
    assert response.json()["settings"] == expected_settings
    assert fake_session.added_quiz is not None
    assert fake_session.added_quiz.settings == expected_settings


def test_organizer_updates_quiz_settings_without_resetting_omitted_values() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    quiz.settings = {
        "time_limit_seconds": 60,
        "shuffle_questions": True,
        "shuffle_answers": True,
        "show_correct_answers": False,
        "scoring_mode": "speed_bonus",
    }
    fake_session = FakeSession(results=[organizer, quiz])
    client = _client_with_session(fake_session)

    response = client.patch(
        f"/quizzes/{quiz.id}",
        json={"settings": {"time_limit_seconds": 90, "shuffle_answers": False}},
        headers=_auth_header(organizer),
    )

    expected_settings = {
        "time_limit_seconds": 90,
        "shuffle_questions": True,
        "shuffle_answers": False,
        "show_correct_answers": False,
        "scoring_mode": "speed_bonus",
    }
    assert response.status_code == 200
    assert response.json()["settings"] == expected_settings
    assert quiz.settings == expected_settings
    assert fake_session.committed is True


def test_update_allows_empty_patch_without_changing_quiz() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    original_title = quiz.title
    original_description = quiz.description
    original_status = quiz.status
    fake_session = FakeSession(results=[organizer, quiz])
    client = _client_with_session(fake_session)

    response = client.patch(
        f"/quizzes/{quiz.id}",
        json={},
        headers=_auth_header(organizer),
    )

    assert response.status_code == 200
    assert quiz.title == original_title
    assert quiz.description == original_description
    assert quiz.status is original_status
    assert fake_session.committed is True


def test_update_allows_description_only_patch() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    original_title = quiz.title
    original_status = quiz.status
    fake_session = FakeSession(results=[organizer, quiz])
    client = _client_with_session(fake_session)

    response = client.patch(
        f"/quizzes/{quiz.id}",
        json={"description": None},
        headers=_auth_header(organizer),
    )

    assert response.status_code == 200
    assert quiz.title == original_title
    assert quiz.description is None
    assert quiz.status is original_status
    assert fake_session.committed is True


def test_update_rejects_null_title_and_data_is_unchanged() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    original_title = quiz.title
    original_status = quiz.status
    fake_session = FakeSession(results=[organizer, quiz])
    client = _client_with_session(fake_session)

    response = client.patch(
        f"/quizzes/{quiz.id}",
        json={"title": None},
        headers=_auth_header(organizer),
    )

    assert response.status_code == 422
    assert quiz.title == original_title
    assert quiz.status is original_status
    assert fake_session.committed is False


def test_update_rejects_null_status_and_data_is_unchanged() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    original_title = quiz.title
    original_status = quiz.status
    fake_session = FakeSession(results=[organizer, quiz])
    client = _client_with_session(fake_session)

    response = client.patch(
        f"/quizzes/{quiz.id}",
        json={"status": None},
        headers=_auth_header(organizer),
    )

    assert response.status_code == 422
    assert quiz.title == original_title
    assert quiz.status is original_status
    assert fake_session.committed is False


def test_update_rejects_null_settings_and_data_is_unchanged() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    original_settings = dict(quiz.settings)
    fake_session = FakeSession(results=[organizer, quiz])
    client = _client_with_session(fake_session)

    response = client.patch(
        f"/quizzes/{quiz.id}",
        json={"settings": None},
        headers=_auth_header(organizer),
    )

    assert response.status_code == 422
    assert quiz.settings == original_settings
    assert fake_session.committed is False


def test_update_rejects_invalid_settings_and_data_is_unchanged() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    original_settings = dict(quiz.settings)
    fake_session = FakeSession(results=[organizer, quiz])
    client = _client_with_session(fake_session)

    response = client.patch(
        f"/quizzes/{quiz.id}",
        json={"settings": {"time_limit_seconds": 3}},
        headers=_auth_header(organizer),
    )

    assert response.status_code == 422
    assert quiz.settings == original_settings
    assert fake_session.committed is False


def test_non_owner_cannot_update_quiz_and_data_is_unchanged() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(uuid4())
    original_title = quiz.title
    original_status = quiz.status
    fake_session = FakeSession(results=[organizer, None])
    client = _client_with_session(fake_session)

    response = client.patch(
        f"/quizzes/{quiz.id}",
        json={"title": "Final Round", "status": "published"},
        headers=_auth_header(organizer),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Quiz not found"}
    assert quiz.title == original_title
    assert quiz.status is original_status
    assert fake_session.committed is False
    assert fake_session.statements[1].compile().params == {
        "id_1": quiz.id,
        "owner_id_1": organizer.id,
    }


def test_organizer_deletes_own_quiz() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    fake_session = FakeSession(results=[organizer, quiz])
    client = _client_with_session(fake_session)

    response = client.delete(f"/quizzes/{quiz.id}", headers=_auth_header(organizer))

    assert response.status_code == 204
    assert response.content == b""
    assert fake_session.deleted_quiz is quiz
    assert fake_session.committed is True


def test_non_owner_cannot_delete_quiz_and_quiz_remains() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(uuid4())
    fake_session = FakeSession(results=[organizer, None])
    client = _client_with_session(fake_session)

    response = client.delete(f"/quizzes/{quiz.id}", headers=_auth_header(organizer))

    assert response.status_code == 404
    assert response.json() == {"detail": "Quiz not found"}
    assert fake_session.deleted_quiz is None
    assert fake_session.committed is False
    assert fake_session.statements[1].compile().params == {
        "id_1": quiz.id,
        "owner_id_1": organizer.id,
    }


def test_participant_cannot_create_quiz() -> None:
    participant = _user("participant@example.com", role=UserRole.PARTICIPANT)
    fake_session = FakeSession(results=[participant])
    client = _client_with_session(fake_session)

    response = client.post(
        "/quizzes",
        json={"title": "Science Bowl"},
        headers=_auth_header(participant),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Organizer role required"}
    assert fake_session.added_quiz is None


def test_participant_cannot_list_quizzes() -> None:
    participant = _user("participant@example.com", role=UserRole.PARTICIPANT)
    fake_session = FakeSession(results=[participant])
    client = _client_with_session(fake_session)

    response = client.get("/quizzes", headers=_auth_header(participant))

    assert response.status_code == 403
    assert response.json() == {"detail": "Organizer role required"}
    assert len(fake_session.statements) == 1


def test_participant_cannot_get_quiz() -> None:
    participant = _user("participant@example.com", role=UserRole.PARTICIPANT)
    quiz_id = uuid4()
    fake_session = FakeSession(results=[participant])
    client = _client_with_session(fake_session)

    response = client.get(f"/quizzes/{quiz_id}", headers=_auth_header(participant))

    assert response.status_code == 403
    assert response.json() == {"detail": "Organizer role required"}
    assert len(fake_session.statements) == 1


def test_participant_cannot_update_quiz() -> None:
    participant = _user("participant@example.com", role=UserRole.PARTICIPANT)
    quiz_id = uuid4()
    fake_session = FakeSession(results=[participant])
    client = _client_with_session(fake_session)

    response = client.patch(
        f"/quizzes/{quiz_id}",
        json={"title": "Final Round"},
        headers=_auth_header(participant),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Organizer role required"}
    assert fake_session.committed is False
    assert len(fake_session.statements) == 1


def test_participant_cannot_delete_quiz() -> None:
    participant = _user("participant@example.com", role=UserRole.PARTICIPANT)
    quiz_id = uuid4()
    fake_session = FakeSession(results=[participant])
    client = _client_with_session(fake_session)

    response = client.delete(f"/quizzes/{quiz_id}", headers=_auth_header(participant))

    assert response.status_code == 403
    assert response.json() == {"detail": "Organizer role required"}
    assert fake_session.deleted_quiz is None
    assert fake_session.committed is False
    assert len(fake_session.statements) == 1
