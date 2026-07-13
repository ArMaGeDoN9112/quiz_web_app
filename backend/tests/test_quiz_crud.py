import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.security import create_access_token
from app.db.session import get_db_session
from app.main import create_app
from app.models import Answer, ChoiceMode, Question, QuestionType, Quiz, QuizStatus, User, UserRole
from app.services.quiz import list_questions, list_quizzes


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

    def scalar_one(self) -> object:
        return self.value

    def scalar(self) -> object | None:
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
    def __init__(
        self,
        results: list[object | list[object] | None],
        commit_error: Exception | None = None,
    ) -> None:
        self.results = results
        self.commit_error = commit_error
        self.statements: list[object] = []
        self.added_quiz: Quiz | None = None
        self.added_question: Question | None = None
        self.deleted_quiz: Quiz | None = None
        self.committed = False
        self.rolled_back = False

    async def execute(self, statement: object) -> FakeScalarResult | FakeListResult:
        self.statements.append(statement)
        result = self.results.pop(0)
        if isinstance(result, list):
            return FakeListResult(result)
        return FakeScalarResult(result)

    def add(self, obj: object) -> None:
        if isinstance(obj, Quiz):
            self.added_quiz = obj
        if isinstance(obj, Question):
            self.added_question = obj

    async def commit(self) -> None:
        if self.commit_error is not None:
            raise self.commit_error
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def refresh(self, obj: object) -> None:
        if isinstance(obj, Quiz):
            obj.id = uuid4()
            obj.created_at = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
            obj.updated_at = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
        if isinstance(obj, Question):
            obj.id = uuid4()
            for answer in obj.answers:
                answer.id = uuid4()

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


def _question(quiz_id: UUID, position: int = 1) -> Question:
    question = Question(
        quiz_id=quiz_id,
        type=QuestionType.TEXT,
        choice_mode=ChoiceMode.SINGLE,
        text="Capital of France?",
        image_url=None,
        points=1,
        position=position,
        answers=[
            Answer(text="Paris", is_correct=True, position=1),
            Answer(text="Rome", is_correct=False, position=2),
        ],
    )
    question.id = uuid4()
    for answer in question.answers:
        answer.id = uuid4()
    return question


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


def test_organizer_lists_questions_for_own_quiz() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    question = _question(quiz.id)
    fake_session = FakeSession(results=[organizer, quiz, [question]])
    client = _client_with_session(fake_session)

    response = client.get(f"/quizzes/{quiz.id}/questions", headers=_auth_header(organizer))

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(question.id),
            "quiz_id": str(quiz.id),
            "type": "text",
            "choice_mode": "single",
            "text": "Capital of France?",
            "image_url": None,
            "points": 1,
            "position": 1,
            "answers": [
                {
                    "id": str(question.answers[0].id),
                    "text": "Paris",
                    "is_correct": True,
                    "position": 1,
                },
                {
                    "id": str(question.answers[1].id),
                    "text": "Rome",
                    "is_correct": False,
                    "position": 2,
                },
            ],
        }
    ]
    assert fake_session.statements[1].compile().params == {
        "id_1": quiz.id,
        "owner_id_1": organizer.id,
    }
    assert fake_session.statements[2].compile().params == {"quiz_id_1": quiz.id}


def test_list_questions_service_returns_owner_quiz_questions_in_query_order() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    first_question = _question(quiz.id, position=1)
    second_question = _question(quiz.id, position=2)
    fake_session = FakeSession(results=[quiz, [first_question, second_question]])

    questions = asyncio.run(list_questions(fake_session, organizer, quiz.id))

    assert questions == [first_question, second_question]
    assert fake_session.statements[0].compile().params == {
        "id_1": quiz.id,
        "owner_id_1": organizer.id,
    }
    assert fake_session.statements[1].compile().params == {"quiz_id_1": quiz.id}


def test_non_owner_cannot_list_questions() -> None:
    organizer = _user("organizer@example.com")
    quiz_id = uuid4()
    fake_session = FakeSession(results=[organizer, None])
    client = _client_with_session(fake_session)

    response = client.get(f"/quizzes/{quiz_id}/questions", headers=_auth_header(organizer))

    assert response.status_code == 404
    assert response.json() == {"detail": "Quiz not found"}
    assert len(fake_session.statements) == 2


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


def test_organizer_adds_text_single_choice_question() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    fake_session = FakeSession(results=[organizer, quiz, 0])
    client = _client_with_session(fake_session)

    response = client.post(
        f"/quizzes/{quiz.id}/questions",
        json={
            "type": "text",
            "choice_mode": "single",
            "text": "Capital of France?",
            "answers": [
                {"text": "Paris", "is_correct": True},
                {"text": "Rome", "is_correct": False},
            ],
        },
        headers=_auth_header(organizer),
    )

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"])
    assert body["quiz_id"] == str(quiz.id)
    assert body["type"] == "text"
    assert body["choice_mode"] == "single"
    assert body["text"] == "Capital of France?"
    assert body["image_url"] is None
    assert body["points"] == 1
    assert body["position"] == 1
    assert [answer["position"] for answer in body["answers"]] == [1, 2]
    assert [answer["is_correct"] for answer in body["answers"]] == [True, False]
    assert fake_session.added_question is not None
    assert fake_session.added_question.quiz_id == quiz.id
    assert fake_session.added_question.position == 1
    assert fake_session.committed is True


def test_organizer_adds_image_multiple_choice_question() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    fake_session = FakeSession(results=[organizer, quiz, 3])
    client = _client_with_session(fake_session)

    response = client.post(
        f"/quizzes/{quiz.id}/questions",
        json={
            "type": "image",
            "choice_mode": "multiple",
            "text": "Select planets shown.",
            "image_url": "https://example.com/planets.png",
            "points": 3,
            "answers": [
                {"text": "Earth", "is_correct": True},
                {"text": "Mars", "is_correct": True},
                {"text": "Moon", "is_correct": False},
            ],
        },
        headers=_auth_header(organizer),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "image"
    assert body["choice_mode"] == "multiple"
    assert body["image_url"] == "https://example.com/planets.png"
    assert body["points"] == 3
    assert body["position"] == 4
    assert [answer["is_correct"] for answer in body["answers"]] == [True, True, False]
    assert fake_session.added_question is not None
    assert fake_session.added_question.position == 4


def test_organizer_adds_image_question_with_http_url() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    fake_session = FakeSession(results=[organizer, quiz, 0])
    client = _client_with_session(fake_session)

    response = client.post(
        f"/quizzes/{quiz.id}/questions",
        json={
            "type": "image",
            "choice_mode": "single",
            "text": "What is shown?",
            "image_url": "http://example.com/object.png",
            "answers": [
                {"text": "A comet", "is_correct": True},
                {"text": "A volcano", "is_correct": False},
            ],
        },
        headers=_auth_header(organizer),
    )

    assert response.status_code == 201
    assert response.json()["image_url"] == "http://example.com/object.png"
    assert fake_session.added_question is not None
    assert fake_session.added_question.image_url == "http://example.com/object.png"


@pytest.mark.parametrize(
    "image_url",
    [
        "javascript:alert(1)",
        "file:///tmp/object.png",
        "not-a-url",
    ],
)
def test_question_create_rejects_non_http_image_url(image_url: str) -> None:
    organizer = _user("organizer@example.com")
    fake_session = FakeSession(results=[organizer])
    client = _client_with_session(fake_session)

    response = client.post(
        f"/quizzes/{uuid4()}/questions",
        json={
            "type": "image",
            "choice_mode": "single",
            "text": "What is shown?",
            "image_url": image_url,
            "answers": [
                {"text": "A comet", "is_correct": True},
                {"text": "A volcano", "is_correct": False},
            ],
        },
        headers=_auth_header(organizer),
    )

    assert response.status_code == 422
    assert fake_session.added_question is None
    assert fake_session.committed is False


def test_question_create_rejects_single_choice_without_exactly_one_correct_answer() -> None:
    organizer = _user("organizer@example.com")
    fake_session = FakeSession(results=[organizer])
    client = _client_with_session(fake_session)

    response = client.post(
        f"/quizzes/{uuid4()}/questions",
        json={
            "type": "text",
            "choice_mode": "single",
            "text": "Capital of France?",
            "answers": [
                {"text": "Paris", "is_correct": True},
                {"text": "Lyon", "is_correct": True},
            ],
        },
        headers=_auth_header(organizer),
    )

    assert response.status_code == 422
    assert fake_session.added_question is None
    assert fake_session.committed is False


def test_question_create_rejects_multiple_choice_with_fewer_than_two_correct_answers() -> None:
    organizer = _user("organizer@example.com")
    fake_session = FakeSession(results=[organizer])
    client = _client_with_session(fake_session)

    response = client.post(
        f"/quizzes/{uuid4()}/questions",
        json={
            "type": "text",
            "choice_mode": "multiple",
            "text": "Select prime numbers.",
            "answers": [
                {"text": "2", "is_correct": True},
                {"text": "4", "is_correct": False},
            ],
        },
        headers=_auth_header(organizer),
    )

    assert response.status_code == 422
    assert fake_session.added_question is None
    assert fake_session.committed is False


def test_question_create_rejects_image_question_without_image_url() -> None:
    organizer = _user("organizer@example.com")
    fake_session = FakeSession(results=[organizer])
    client = _client_with_session(fake_session)

    response = client.post(
        f"/quizzes/{uuid4()}/questions",
        json={
            "type": "image",
            "choice_mode": "single",
            "text": "What is shown?",
            "answers": [
                {"text": "A comet", "is_correct": True},
                {"text": "A volcano", "is_correct": False},
            ],
        },
        headers=_auth_header(organizer),
    )

    assert response.status_code == 422
    assert fake_session.added_question is None
    assert fake_session.committed is False


def test_non_owner_cannot_add_question_to_quiz() -> None:
    organizer = _user("organizer@example.com")
    quiz_id = uuid4()
    fake_session = FakeSession(results=[organizer, None])
    client = _client_with_session(fake_session)

    response = client.post(
        f"/quizzes/{quiz_id}/questions",
        json={
            "type": "text",
            "choice_mode": "single",
            "text": "Capital of France?",
            "answers": [
                {"text": "Paris", "is_correct": True},
                {"text": "Rome", "is_correct": False},
            ],
        },
        headers=_auth_header(organizer),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Quiz not found"}
    assert fake_session.added_question is None
    assert fake_session.committed is False


def test_participant_cannot_add_question_to_quiz() -> None:
    participant = _user("participant@example.com", role=UserRole.PARTICIPANT)
    fake_session = FakeSession(results=[participant])
    client = _client_with_session(fake_session)

    response = client.post(
        f"/quizzes/{uuid4()}/questions",
        json={
            "type": "text",
            "choice_mode": "single",
            "text": "Capital of France?",
            "answers": [
                {"text": "Paris", "is_correct": True},
                {"text": "Rome", "is_correct": False},
            ],
        },
        headers=_auth_header(participant),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Organizer role required"}
    assert fake_session.added_question is None
    assert fake_session.committed is False
    assert len(fake_session.statements) == 1


def test_question_position_conflict_returns_409() -> None:
    organizer = _user("organizer@example.com")
    quiz = _quiz(organizer.id)
    fake_session = FakeSession(
        results=[organizer, quiz, 0],
        commit_error=IntegrityError("insert question", {}, Exception("unique conflict")),
    )
    client = _client_with_session(fake_session)

    response = client.post(
        f"/quizzes/{quiz.id}/questions",
        json={
            "type": "text",
            "choice_mode": "single",
            "text": "Capital of France?",
            "answers": [
                {"text": "Paris", "is_correct": True},
                {"text": "Rome", "is_correct": False},
            ],
        },
        headers=_auth_header(organizer),
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Question position conflict; retry request"}
    assert fake_session.rolled_back is True
