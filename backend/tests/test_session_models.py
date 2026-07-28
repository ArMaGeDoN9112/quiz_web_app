from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import ForeignKeyConstraint, UniqueConstraint

from app.db.base import Base
from app.models import (
    ChoiceMode,
    QuestionEvent,
    QuestionEventStatus,
    QuestionResponse,
    QuestionType,
    QuizSession,
    SessionParticipant,
    SessionStatus,
)
from app.schemas.session import SessionLiveUpdateResponse
from app.services.scoring import RankedScore
from app.services.session import (
    ActiveQuestion,
    ActiveQuestionAnswer,
    QuizSessionError,
    SessionQuizNotFoundError,
    SessionScoreboard,
)


def test_session_domain_errors_share_a_base_class() -> None:
    assert issubclass(SessionQuizNotFoundError, QuizSessionError)


def test_live_update_schema_accepts_session_service_results() -> None:
    session_id = uuid4()
    participant_id = uuid4()
    scoreboard = SessionScoreboard(
        session_id=session_id,
        status=SessionStatus.ACTIVE,
        entries=[
            RankedScore(
                participant_id=participant_id,
                display_name="Ada",
                score=10,
                rank=1,
            )
        ],
        winner_ids=[participant_id],
    )
    question_id = uuid4()
    current_question = ActiveQuestion(
        event_id=uuid4(),
        session_id=session_id,
        question_id=question_id,
        type=QuestionType.TEXT,
        choice_mode=ChoiceMode.SINGLE,
        text="Question?",
        image_url=None,
        ends_at=datetime(2026, 7, 7, 12, 0, 30, tzinfo=UTC),
        shuffle_answers=False,
        answers=[ActiveQuestionAnswer(id=uuid4(), text="Answer", position=1)],
    )

    update = SessionLiveUpdateResponse.model_validate(
        {"scoreboard": scoreboard, "current_question": current_question}
    )

    assert update.scoreboard.entries[0].participant_id == participant_id
    assert update.current_question is not None
    assert update.current_question.question_id == question_id


def test_session_timestamps_are_timezone_aware() -> None:
    assert QuizSession.__table__.c.ended_at.type.timezone is True
    assert QuestionEvent.__table__.c.started_at.type.timezone is True
    assert QuestionEvent.__table__.c.ended_at.type.timezone is True


def test_session_models_are_registered_with_metadata() -> None:
    assert QuizSession.__table__ in Base.metadata.tables.values()
    assert SessionParticipant.__table__ in Base.metadata.tables.values()
    assert QuestionEvent.__table__ in Base.metadata.tables.values()
    assert QuestionResponse.__table__ in Base.metadata.tables.values()


def test_sessions_table_matches_database_contract() -> None:
    table = QuizSession.__table__
    unique_columns = {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert table.name == "sessions"
    assert set(table.c.keys()) == {
        "id",
        "quiz_id",
        "organizer_id",
        "room_code",
        "status",
        "created_at",
        "updated_at",
        "ended_at",
        "final_results",
    }
    assert SessionStatus.__members__.keys() == {"WAITING", "ACTIVE", "ENDED"}
    assert table.c.status.type.enums == ["waiting", "active", "ended"]
    assert table.c.quiz_id.nullable is False
    assert table.c.organizer_id.nullable is False
    assert table.c.room_code.nullable is False
    assert ("room_code",) in unique_columns


def test_session_participants_table_matches_database_contract() -> None:
    table = SessionParticipant.__table__
    unique_columns = {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert table.name == "session_participants"
    assert set(table.c.keys()) == {
        "id",
        "session_id",
        "user_id",
        "display_name",
        "joined_at",
    }
    assert table.c.session_id.nullable is False
    assert table.c.user_id.nullable is False
    assert table.c.display_name.nullable is False
    assert ("session_id", "user_id") in unique_columns


def test_question_events_table_matches_database_contract() -> None:
    table = QuestionEvent.__table__
    unique_columns = {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert table.name == "question_events"
    assert set(table.c.keys()) == {
        "id",
        "session_id",
        "question_id",
        "status",
        "started_at",
        "ended_at",
    }
    assert QuestionEventStatus.__members__.keys() == {"SCHEDULED", "ACTIVE", "CLOSED"}
    assert table.c.status.type.enums == ["scheduled", "active", "closed"]
    assert table.c.session_id.nullable is False
    assert table.c.question_id.nullable is False
    assert ("session_id", "question_id") in unique_columns


def test_question_responses_table_matches_database_contract() -> None:
    table = QuestionResponse.__table__
    unique_columns = {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert table.name == "question_responses"
    assert set(table.c.keys()) == {
        "id",
        "participant_id",
        "question_event_id",
        "selected_answer_ids",
        "text_answer",
        "awarded_points",
        "submitted_at",
        "meta",
    }
    assert table.c.participant_id.nullable is False
    assert table.c.question_event_id.nullable is False
    assert table.c.selected_answer_ids.nullable is False
    assert table.c.text_answer.nullable is True
    assert table.c.awarded_points.nullable is False
    assert table.c.meta.nullable is False
    assert ("participant_id", "question_event_id") in unique_columns


def test_session_models_have_expected_foreign_keys() -> None:
    foreign_keys = {
        (constraint.name, tuple(constraint.column_keys), constraint.elements[0].target_fullname)
        for table in (
            QuizSession.__table__,
            SessionParticipant.__table__,
            QuestionEvent.__table__,
            QuestionResponse.__table__,
        )
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }

    assert ("fk_sessions_quiz_id_quizzes", ("quiz_id",), "quizzes.id") in foreign_keys
    assert ("fk_sessions_organizer_id_users", ("organizer_id",), "users.id") in foreign_keys
    assert (
        "fk_session_participants_session_id_sessions",
        ("session_id",),
        "sessions.id",
    ) in foreign_keys
    assert (
        "fk_session_participants_user_id_users",
        ("user_id",),
        "users.id",
    ) in foreign_keys
    assert (
        "fk_question_events_session_id_sessions",
        ("session_id",),
        "sessions.id",
    ) in foreign_keys
    assert (
        "fk_question_events_question_id_questions",
        ("question_id",),
        "questions.id",
    ) in foreign_keys
    assert (
        "fk_question_responses_participant_id_session_participants",
        ("participant_id",),
        "session_participants.id",
    ) in foreign_keys
    assert (
        "fk_question_responses_question_event_id_question_events",
        ("question_event_id",),
        "question_events.id",
    ) in foreign_keys
