from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.session import get_db_session
from app.main import create_app
from app.models import Quiz, QuizSession, SessionParticipant, SessionStatus, User, UserRole


class FakeScalarResult:
    def __init__(self, value: object | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object | None:
        return self.value


class FakeRowsResult:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows

    def all(self) -> list[tuple[object, ...]]:
        return self.rows


class FakeSession:
    def __init__(self, results: list[object]) -> None:
        self.results = results

    async def execute(self, statement: object) -> object:
        return self.results.pop(0)


def _user(email: str, role: UserRole) -> User:
    user = User(email=email, password_hash="hash", role=role)
    user.id = uuid4()
    user.created_at = datetime(2026, 7, 13, 10, 0, tzinfo=UTC)
    user.updated_at = datetime(2026, 7, 13, 10, 0, tzinfo=UTC)
    return user


def _session(organizer: User) -> QuizSession:
    quiz_session = QuizSession(
        quiz_id=uuid4(),
        organizer_id=organizer.id,
        room_code="ABC123",
        status=SessionStatus.ENDED,
    )
    quiz_session.id = uuid4()
    quiz_session.created_at = datetime(2026, 7, 13, 10, 0, tzinfo=UTC)
    quiz_session.updated_at = datetime(2026, 7, 13, 11, 0, tzinfo=UTC)
    quiz_session.ended_at = datetime(2026, 7, 13, 11, 0, tzinfo=UTC)
    return quiz_session


def _quiz(quiz_session: QuizSession) -> Quiz:
    quiz = Quiz(
        owner_id=quiz_session.organizer_id,
        title="Science Bowl",
        description=None,
        settings={},
    )
    quiz.id = quiz_session.quiz_id
    quiz.created_at = datetime(2026, 7, 13, 9, 0, tzinfo=UTC)
    quiz.updated_at = datetime(2026, 7, 13, 9, 0, tzinfo=UTC)
    return quiz


def _participant(quiz_session: QuizSession, user: User, name: str = "Ada") -> SessionParticipant:
    participant = SessionParticipant(
        session_id=quiz_session.id,
        user_id=user.id,
        display_name=name,
    )
    participant.id = uuid4()
    participant.joined_at = datetime(2026, 7, 13, 10, 5, tzinfo=UTC)
    return participant


def _finalize(quiz_session: QuizSession, participants: list[SessionParticipant]) -> None:
    quiz_session.final_results = {
        "entries": [
            {
                "participant_id": str(participant.id),
                "display_name": participant.display_name,
                "score": 10 - index,
                "rank": index + 1,
            }
            for index, participant in enumerate(participants)
        ],
        "winner_ids": [str(participants[0].id)],
    }


def _client(fake_session: FakeSession) -> TestClient:
    app = create_app()

    async def override_get_db_session():
        yield fake_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app)


def _headers(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_participant_history_returns_only_current_user_ended_sessions() -> None:
    organizer = _user("organizer@example.com", UserRole.ORGANIZER)
    participant = _user("participant@example.com", UserRole.PARTICIPANT)
    quiz_session = _session(organizer)
    quiz = _quiz(quiz_session)
    session_participant = _participant(quiz_session, participant)
    _finalize(quiz_session, [session_participant])
    client = _client(
        FakeSession(
            [
                FakeScalarResult(participant),
                FakeRowsResult([(session_participant, quiz_session, quiz)]),
            ]
        )
    )

    response = client.get("/sessions/history/participated", headers=_headers(participant))

    assert response.status_code == 200
    assert response.json() == [
        {
            "session_id": str(quiz_session.id),
            "quiz_id": str(quiz.id),
            "quiz_title": "Science Bowl",
            "ended_at": "2026-07-13T11:00:00Z",
            "score": 10,
            "rank": 1,
            "participant_count": 1,
        }
    ]


def test_organizer_history_returns_conducted_session_winners() -> None:
    organizer = _user("organizer@example.com", UserRole.ORGANIZER)
    quiz_session = _session(organizer)
    quiz = _quiz(quiz_session)
    winner = _participant(quiz_session, _user("winner@example.com", UserRole.PARTICIPANT))
    runner_up = _participant(quiz_session, _user("runner@example.com", UserRole.PARTICIPANT), "Bert")
    _finalize(quiz_session, [winner, runner_up])
    client = _client(
        FakeSession(
            [
                FakeScalarResult(organizer),
                FakeRowsResult([(quiz_session, quiz)]),
            ]
        )
    )

    response = client.get("/sessions/history/conducted", headers=_headers(organizer))

    assert response.status_code == 200
    assert response.json()[0]["participant_count"] == 2
    assert response.json()[0]["winner_names"] == ["Ada"]


def test_result_detail_allows_organizer_or_session_participant_only() -> None:
    organizer = _user("organizer@example.com", UserRole.ORGANIZER)
    participant = _user("participant@example.com", UserRole.PARTICIPANT)
    outsider = _user("outsider@example.com", UserRole.PARTICIPANT)
    quiz_session = _session(organizer)
    quiz = _quiz(quiz_session)
    session_participant = _participant(quiz_session, participant)
    _finalize(quiz_session, [session_participant])

    allowed_client = _client(
        FakeSession(
            [
                FakeScalarResult(participant),
                FakeRowsResult([(quiz_session, quiz)]),
                FakeScalarResult(session_participant),
            ]
        )
    )
    allowed = allowed_client.get(f"/sessions/{quiz_session.id}/result", headers=_headers(participant))

    assert allowed.status_code == 200
    assert allowed.json()["winner_ids"] == [str(session_participant.id)]
    assert allowed.json()["entries"][0]["score"] == 10

    denied_client = _client(
        FakeSession(
            [
                FakeScalarResult(outsider),
                FakeRowsResult([(quiz_session, quiz)]),
                FakeScalarResult(None),
            ]
        )
    )
    denied = denied_client.get(f"/sessions/{quiz_session.id}/result", headers=_headers(outsider))

    assert denied.status_code == 403
    assert denied.json() == {"detail": "Session result access denied"}


def test_organizer_can_view_finalized_empty_session_result() -> None:
    organizer = _user("organizer@example.com", UserRole.ORGANIZER)
    quiz_session = _session(organizer)
    quiz = _quiz(quiz_session)
    quiz_session.final_results = {"entries": [], "winner_ids": []}
    client = _client(
        FakeSession(
            [
                FakeScalarResult(organizer),
                FakeRowsResult([(quiz_session, quiz)]),
            ]
        )
    )

    response = client.get(f"/sessions/{quiz_session.id}/result", headers=_headers(organizer))

    assert response.status_code == 200
    assert response.json()["participant_count"] == 0
    assert response.json()["entries"] == []


def test_history_endpoints_require_matching_role() -> None:
    organizer = _user("organizer@example.com", UserRole.ORGANIZER)
    participant = _user("participant@example.com", UserRole.PARTICIPANT)

    participant_client = _client(FakeSession([FakeScalarResult(participant)]))
    organizer_client = _client(FakeSession([FakeScalarResult(organizer)]))

    assert participant_client.get("/sessions/history/conducted", headers=_headers(participant)).status_code == 403
    assert organizer_client.get("/sessions/history/participated", headers=_headers(organizer)).status_code == 403
