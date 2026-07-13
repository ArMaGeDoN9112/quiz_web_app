import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.session import get_db_session
from app.main import create_app
from app.models import (
    Answer,
    ChoiceMode,
    Question,
    QuestionEvent,
    QuestionEventStatus,
    QuestionResponse,
    QuestionType,
    QuizSession,
    SessionParticipant,
    SessionStatus,
    User,
    UserRole,
)
from app.services.session import (
    AnswerOutsideQuestionWindowError,
    AnswerSessionEndedError,
    DuplicateQuestionResponseError,
    InvalidQuestionAnswerSelectionError,
    QuestionNotInSessionQuizError,
    StartQuestionSessionEndedError,
    SessionQuestionNotFoundError,
    StartQuestionSessionNotFoundError,
    submit_answer,
    end_session,
    start_question,
)


class FakeScalarResult:
    def __init__(self, value: object | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object | None:
        return self.value

    def scalars(self) -> "FakeScalarResult":
        return self

    def all(self) -> list[object]:
        if self.value is None:
            return []
        if isinstance(self.value, list):
            return self.value
        return [self.value]


class FakeSession:
    def __init__(self, results: list[object | None]) -> None:
        self.results = results
        self.statements: list[object] = []
        self.added: list[object] = []
        self.committed = False
        self.rolled_back = False

    async def execute(self, statement: object) -> FakeScalarResult:
        self.statements.append(statement)
        return FakeScalarResult(self.results.pop(0))

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def flush(self) -> None:
        pass

    async def refresh(self, obj: object) -> None:
        if isinstance(obj, QuestionEvent):
            obj.id = uuid4()
        if isinstance(obj, QuestionResponse):
            obj.id = uuid4()
            obj.submitted_at = datetime(2026, 7, 7, 12, 0, 10, tzinfo=UTC)


def _user(email: str, role: UserRole) -> User:
    user = User(email=email, password_hash="hashed-password", role=role)
    user.id = uuid4()
    user.created_at = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    user.updated_at = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    return user


def _quiz_session(organizer_id: UUID, status: SessionStatus = SessionStatus.WAITING) -> QuizSession:
    quiz_session = QuizSession(
        quiz_id=uuid4(),
        organizer_id=organizer_id,
        room_code="ABC123",
        status=status,
    )
    quiz_session.id = uuid4()
    quiz_session.created_at = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    quiz_session.updated_at = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    return quiz_session


def _question(quiz_id: UUID, choice_mode: ChoiceMode = ChoiceMode.SINGLE) -> Question:
    question = Question(
        quiz_id=quiz_id,
        type=QuestionType.TEXT,
        choice_mode=choice_mode,
        text="Capital of France?",
        points=1,
        position=1,
    )
    question.id = uuid4()
    return question


def _answer(question: Question) -> Answer:
    answer = Answer(
        question_id=question.id,
        text="Paris",
        is_correct=True,
        position=1,
    )
    answer.id = uuid4()
    return answer


def _participant(quiz_session: QuizSession, user: User) -> SessionParticipant:
    participant = SessionParticipant(
        session_id=quiz_session.id,
        user_id=user.id,
        display_name="Ada",
    )
    participant.id = uuid4()
    participant.joined_at = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    return participant


def _active_event(quiz_session: QuizSession, question: Question) -> QuestionEvent:
    event = QuestionEvent(
        session_id=quiz_session.id,
        question_id=question.id,
        status=QuestionEventStatus.ACTIVE,
        started_at=datetime(2026, 7, 7, 12, 0, tzinfo=UTC),
        ended_at=datetime(2026, 7, 7, 12, 0, 30, tzinfo=UTC),
    )
    event.id = uuid4()
    return event


def _client_with_session(fake_session: FakeSession) -> TestClient:
    app = create_app()

    async def override_get_db_session():
        yield fake_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app)


def _auth_header(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_start_question_sets_active_window_with_deterministic_time() -> None:
    organizer = _user("organizer@example.com", UserRole.ORGANIZER)
    quiz_session = _quiz_session(organizer.id)
    question = _question(quiz_session.quiz_id)
    now = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    fake_session = FakeSession(results=[quiz_session, question, None])

    event = asyncio.run(
        start_question(
            fake_session,
            organizer,
            quiz_session.id,
            question.id,
            now_factory=lambda: now,
            duration_seconds=45,
        )
    )

    assert event.session_id == quiz_session.id
    assert event.question_id == question.id
    assert event.status is QuestionEventStatus.ACTIVE
    assert event.started_at == now
    assert event.ended_at == now + timedelta(seconds=45)
    assert quiz_session.status is SessionStatus.ACTIVE
    assert fake_session.committed is True


def test_start_question_without_duration_stays_open_for_manual_mode() -> None:
    organizer = _user("organizer@example.com", UserRole.ORGANIZER)
    quiz_session = _quiz_session(organizer.id)
    question = _question(quiz_session.quiz_id)
    now = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    fake_session = FakeSession(results=[quiz_session, question, None])

    event = asyncio.run(
        start_question(
            fake_session,
            organizer,
            quiz_session.id,
            question.id,
            now_factory=lambda: now,
        )
    )

    assert event.started_at == now
    assert event.ended_at is None


def test_start_question_closes_existing_active_question() -> None:
    organizer = _user("organizer@example.com", UserRole.ORGANIZER)
    quiz_session = _quiz_session(organizer.id, SessionStatus.ACTIVE)
    question = _question(quiz_session.quiz_id)
    active_question = _question(quiz_session.quiz_id)
    existing_event = _active_event(quiz_session, active_question)
    now = datetime(2026, 7, 7, 12, 1, tzinfo=UTC)
    fake_session = FakeSession(results=[quiz_session, question, existing_event])

    asyncio.run(
        start_question(
            fake_session,
            organizer,
            quiz_session.id,
            question.id,
            now_factory=lambda: now,
            duration_seconds=30,
        )
    )

    assert existing_event.status is QuestionEventStatus.CLOSED
    assert existing_event.ended_at == now


def test_start_question_rejects_session_not_owned_by_organizer() -> None:
    organizer = _user("organizer@example.com", UserRole.ORGANIZER)
    fake_session = FakeSession(results=[None])

    try:
        asyncio.run(
            start_question(
                fake_session,
                organizer,
                uuid4(),
                uuid4(),
                now_factory=lambda: datetime(2026, 7, 7, 12, 0, tzinfo=UTC),
            )
        )
    except StartQuestionSessionNotFoundError:
        pass
    else:
        raise AssertionError("Expected StartQuestionSessionNotFoundError")


def test_start_question_rejects_question_from_other_quiz() -> None:
    organizer = _user("organizer@example.com", UserRole.ORGANIZER)
    quiz_session = _quiz_session(organizer.id)
    question = _question(uuid4())
    fake_session = FakeSession(results=[quiz_session, question])

    try:
        asyncio.run(
            start_question(
                fake_session,
                organizer,
                quiz_session.id,
                question.id,
                now_factory=lambda: datetime(2026, 7, 7, 12, 0, tzinfo=UTC),
            )
        )
    except QuestionNotInSessionQuizError:
        pass
    else:
        raise AssertionError("Expected QuestionNotInSessionQuizError")


def test_start_question_rejects_ended_session() -> None:
    organizer = _user("organizer@example.com", UserRole.ORGANIZER)
    quiz_session = _quiz_session(organizer.id, SessionStatus.ENDED)
    question = _question(quiz_session.quiz_id)
    fake_session = FakeSession(results=[quiz_session, question])

    try:
        asyncio.run(
            start_question(
                fake_session,
                organizer,
                quiz_session.id,
                question.id,
                now_factory=lambda: datetime(2026, 7, 7, 12, 0, tzinfo=UTC),
            )
        )
    except StartQuestionSessionEndedError:
        pass
    else:
        raise AssertionError("Expected StartQuestionSessionEndedError")

    assert fake_session.added == []


def test_submit_answer_accepts_response_inside_active_window() -> None:
    participant_user = _user("participant@example.com", UserRole.PARTICIPANT)
    quiz_session = _quiz_session(uuid4(), SessionStatus.ACTIVE)
    question = _question(quiz_session.quiz_id)
    participant = _participant(quiz_session, participant_user)
    event = _active_event(quiz_session, question)
    answer_id = uuid4()
    answer = Answer(
        question_id=question.id,
        text="Paris",
        is_correct=True,
        position=1,
    )
    answer.id = answer_id
    fake_session = FakeSession(results=[quiz_session, participant, event, question, [answer], None])

    response = asyncio.run(
        submit_answer(
            fake_session,
            participant_user,
            quiz_session.id,
            question.id,
            selected_answer_ids=[answer_id],
            text_answer=None,
            now_factory=lambda: datetime(2026, 7, 7, 12, 0, 10, tzinfo=UTC),
        )
    )

    assert response.participant_id == participant.id
    assert response.question_event_id == event.id
    assert response.selected_answer_ids == [str(answer_id)]
    assert response.awarded_points == question.points
    assert fake_session.committed is True


def test_submit_answer_rejects_before_question_window() -> None:
    participant_user = _user("participant@example.com", UserRole.PARTICIPANT)
    quiz_session = _quiz_session(uuid4(), SessionStatus.ACTIVE)
    question = _question(quiz_session.quiz_id)
    participant = _participant(quiz_session, participant_user)
    event = _active_event(quiz_session, question)
    fake_session = FakeSession(results=[quiz_session, participant, event])

    try:
        asyncio.run(
            submit_answer(
                fake_session,
                participant_user,
                quiz_session.id,
                question.id,
                selected_answer_ids=[uuid4()],
                text_answer=None,
                now_factory=lambda: datetime(2026, 7, 7, 11, 59, 59, tzinfo=UTC),
            )
        )
    except AnswerOutsideQuestionWindowError:
        pass
    else:
        raise AssertionError("Expected AnswerOutsideQuestionWindowError")

    assert fake_session.added == []


def test_submit_answer_rejects_after_question_window() -> None:
    participant_user = _user("participant@example.com", UserRole.PARTICIPANT)
    quiz_session = _quiz_session(uuid4(), SessionStatus.ACTIVE)
    question = _question(quiz_session.quiz_id)
    participant = _participant(quiz_session, participant_user)
    event = _active_event(quiz_session, question)
    fake_session = FakeSession(results=[quiz_session, participant, event])

    try:
        asyncio.run(
            submit_answer(
                fake_session,
                participant_user,
                quiz_session.id,
                question.id,
                selected_answer_ids=[uuid4()],
                text_answer=None,
                now_factory=lambda: datetime(2026, 7, 7, 12, 0, 31, tzinfo=UTC),
            )
        )
    except AnswerOutsideQuestionWindowError:
        pass
    else:
        raise AssertionError("Expected AnswerOutsideQuestionWindowError")

    assert fake_session.added == []


def test_submit_answer_rejects_duplicate_response() -> None:
    participant_user = _user("participant@example.com", UserRole.PARTICIPANT)
    quiz_session = _quiz_session(uuid4(), SessionStatus.ACTIVE)
    question = _question(quiz_session.quiz_id)
    participant = _participant(quiz_session, participant_user)
    event = _active_event(quiz_session, question)
    existing_response = QuestionResponse(
        participant_id=participant.id,
        question_event_id=event.id,
        selected_answer_ids=[],
        text_answer=None,
        meta={},
    )
    answer_id = uuid4()
    answer = Answer(
        question_id=question.id,
        text="Paris",
        is_correct=True,
        position=1,
    )
    answer.id = answer_id
    fake_session = FakeSession(
        results=[quiz_session, participant, event, question, [answer], existing_response]
    )

    try:
        asyncio.run(
            submit_answer(
                fake_session,
                participant_user,
                quiz_session.id,
                question.id,
                selected_answer_ids=[answer_id],
                text_answer=None,
                now_factory=lambda: datetime(2026, 7, 7, 12, 0, 10, tzinfo=UTC),
            )
        )
    except DuplicateQuestionResponseError:
        pass
    else:
        raise AssertionError("Expected DuplicateQuestionResponseError")

    assert fake_session.added == []


def test_submit_answer_rejects_foreign_answer_id() -> None:
    participant_user = _user("participant@example.com", UserRole.PARTICIPANT)
    quiz_session = _quiz_session(uuid4(), SessionStatus.ACTIVE)
    question = _question(quiz_session.quiz_id)
    participant = _participant(quiz_session, participant_user)
    event = _active_event(quiz_session, question)
    valid_answer = _answer(question)
    fake_session = FakeSession(results=[quiz_session, participant, event, question, [valid_answer]])

    try:
        asyncio.run(
            submit_answer(
                fake_session,
                participant_user,
                quiz_session.id,
                question.id,
                selected_answer_ids=[uuid4()],
                text_answer=None,
                now_factory=lambda: datetime(2026, 7, 7, 12, 0, 10, tzinfo=UTC),
            )
        )
    except InvalidQuestionAnswerSelectionError:
        pass
    else:
        raise AssertionError("Expected InvalidQuestionAnswerSelectionError")

    assert fake_session.added == []


def test_submit_answer_rejects_empty_answer_selection() -> None:
    participant_user = _user("participant@example.com", UserRole.PARTICIPANT)
    quiz_session = _quiz_session(uuid4(), SessionStatus.ACTIVE)
    question = _question(quiz_session.quiz_id)
    participant = _participant(quiz_session, participant_user)
    event = _active_event(quiz_session, question)
    fake_session = FakeSession(results=[quiz_session, participant, event, question])

    try:
        asyncio.run(
            submit_answer(
                fake_session,
                participant_user,
                quiz_session.id,
                question.id,
                selected_answer_ids=[],
                text_answer=None,
                now_factory=lambda: datetime(2026, 7, 7, 12, 0, 10, tzinfo=UTC),
            )
        )
    except InvalidQuestionAnswerSelectionError:
        pass
    else:
        raise AssertionError("Expected InvalidQuestionAnswerSelectionError")

    assert fake_session.added == []


def test_submit_answer_rejects_multiple_answers_for_single_choice() -> None:
    participant_user = _user("participant@example.com", UserRole.PARTICIPANT)
    quiz_session = _quiz_session(uuid4(), SessionStatus.ACTIVE)
    question = _question(quiz_session.quiz_id, ChoiceMode.SINGLE)
    participant = _participant(quiz_session, participant_user)
    event = _active_event(quiz_session, question)
    first_answer = _answer(question)
    second_answer = _answer(question)
    fake_session = FakeSession(
        results=[quiz_session, participant, event, question, [first_answer, second_answer]]
    )

    try:
        asyncio.run(
            submit_answer(
                fake_session,
                participant_user,
                quiz_session.id,
                question.id,
                selected_answer_ids=[first_answer.id, second_answer.id],
                text_answer=None,
                now_factory=lambda: datetime(2026, 7, 7, 12, 0, 10, tzinfo=UTC),
            )
        )
    except InvalidQuestionAnswerSelectionError:
        pass
    else:
        raise AssertionError("Expected InvalidQuestionAnswerSelectionError")

    assert fake_session.added == []


def test_submit_answer_rejects_duplicate_selected_answer_id() -> None:
    participant_user = _user("participant@example.com", UserRole.PARTICIPANT)
    quiz_session = _quiz_session(uuid4(), SessionStatus.ACTIVE)
    question = _question(quiz_session.quiz_id)
    participant = _participant(quiz_session, participant_user)
    event = _active_event(quiz_session, question)
    answer = _answer(question)
    fake_session = FakeSession(results=[quiz_session, participant, event, question, [answer]])

    try:
        asyncio.run(
            submit_answer(
                fake_session,
                participant_user,
                quiz_session.id,
                question.id,
                selected_answer_ids=[answer.id, answer.id],
                text_answer=None,
                now_factory=lambda: datetime(2026, 7, 7, 12, 0, 10, tzinfo=UTC),
            )
        )
    except InvalidQuestionAnswerSelectionError:
        pass
    else:
        raise AssertionError("Expected InvalidQuestionAnswerSelectionError")

    assert fake_session.added == []


def test_end_session_stores_final_rankings_and_winners() -> None:
    organizer = _user("organizer@example.com", UserRole.ORGANIZER)
    quiz_session = _quiz_session(organizer.id, SessionStatus.ACTIVE)
    question = _question(quiz_session.quiz_id)
    event = _active_event(quiz_session, question)
    first_user = _user("ada@example.com", UserRole.PARTICIPANT)
    second_user = _user("bert@example.com", UserRole.PARTICIPANT)
    first_participant = _participant(quiz_session, first_user)
    second_participant = _participant(quiz_session, second_user)
    second_participant.display_name = "Bert"
    first_response = QuestionResponse(
        participant_id=first_participant.id,
        question_event_id=event.id,
        selected_answer_ids=[],
        text_answer=None,
        awarded_points=8,
        meta={},
    )
    second_response = QuestionResponse(
        participant_id=second_participant.id,
        question_event_id=event.id,
        selected_answer_ids=[],
        text_answer=None,
        awarded_points=4,
        meta={},
    )
    fake_session = FakeSession(
        results=[quiz_session, event, quiz_session, [first_participant, second_participant], [first_response, second_response]]
    )

    scoreboard = asyncio.run(
        end_session(
            fake_session,
            organizer,
            quiz_session.id,
            now_factory=lambda: datetime(2026, 7, 7, 12, 1, tzinfo=UTC),
        )
    )

    assert quiz_session.status is SessionStatus.ENDED
    assert event.status is QuestionEventStatus.CLOSED
    assert scoreboard.entries[0]["rank"] == 1
    assert scoreboard.winner_ids == [first_participant.id]
    assert quiz_session.final_results == {
        "entries": [
            {"participant_id": str(first_participant.id), "display_name": "Ada", "score": 8, "rank": 1},
            {"participant_id": str(second_participant.id), "display_name": "Bert", "score": 4, "rank": 2},
        ],
        "winner_ids": [str(first_participant.id)],
    }


def test_submit_answer_rejects_ended_session() -> None:
    participant_user = _user("participant@example.com", UserRole.PARTICIPANT)
    quiz_session = _quiz_session(uuid4(), SessionStatus.ENDED)
    question = _question(quiz_session.quiz_id)
    fake_session = FakeSession(results=[quiz_session])

    try:
        asyncio.run(
            submit_answer(
                fake_session,
                participant_user,
                quiz_session.id,
                question.id,
                selected_answer_ids=[uuid4()],
                text_answer=None,
                now_factory=lambda: datetime(2026, 7, 7, 12, 0, 10, tzinfo=UTC),
            )
        )
    except AnswerSessionEndedError:
        pass
    else:
        raise AssertionError("Expected AnswerSessionEndedError")

    assert fake_session.added == []


def test_start_question_endpoint_returns_active_event() -> None:
    organizer = _user("organizer@example.com", UserRole.ORGANIZER)
    quiz_session = _quiz_session(organizer.id)
    question = _question(quiz_session.quiz_id)
    fake_session = FakeSession(results=[organizer, quiz_session, question, None])
    client = _client_with_session(fake_session)

    response = client.post(
        f"/sessions/{quiz_session.id}/questions/current",
        json={"question_id": str(question.id), "duration_seconds": 45},
        headers=_auth_header(organizer),
    )

    assert response.status_code == 200
    body = response.json()
    assert UUID(body["id"])
    assert body["session_id"] == str(quiz_session.id)
    assert body["question_id"] == str(question.id)
    assert body["status"] == "active"
    assert body["started_at"] is not None
    assert body["ended_at"] is not None


def test_start_question_endpoint_requires_organizer_role() -> None:
    participant_user = _user("participant@example.com", UserRole.PARTICIPANT)
    fake_session = FakeSession(results=[participant_user])
    client = _client_with_session(fake_session)

    response = client.post(
        f"/sessions/{uuid4()}/questions/current",
        json={"question_id": str(uuid4()), "duration_seconds": 45},
        headers=_auth_header(participant_user),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Organizer role required"}


def test_submit_answer_endpoint_maps_closed_window_to_409() -> None:
    participant_user = _user("participant@example.com", UserRole.PARTICIPANT)
    quiz_session = _quiz_session(uuid4(), SessionStatus.ACTIVE)
    question = _question(quiz_session.quiz_id)
    participant = _participant(quiz_session, participant_user)
    event = _active_event(quiz_session, question)
    event.ended_at = datetime(2020, 1, 1, tzinfo=UTC)
    fake_session = FakeSession(results=[participant_user, quiz_session, participant, event])
    client = _client_with_session(fake_session)

    response = client.post(
        f"/sessions/{quiz_session.id}/answer",
        json={"question_id": str(question.id), "selected_answer_ids": [str(uuid4())]},
        headers=_auth_header(participant_user),
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Question is not accepting answers"}


def test_submit_answer_endpoint_requires_participant_role() -> None:
    organizer = _user("organizer@example.com", UserRole.ORGANIZER)
    fake_session = FakeSession(results=[organizer])
    client = _client_with_session(fake_session)

    response = client.post(
        f"/sessions/{uuid4()}/answer",
        json={"question_id": str(uuid4()), "selected_answer_ids": [str(uuid4())]},
        headers=_auth_header(organizer),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Participant role required"}
