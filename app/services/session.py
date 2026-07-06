import secrets
import string
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Answer,
    ChoiceMode,
    Question,
    QuestionEvent,
    QuestionEventStatus,
    QuestionResponse,
    Quiz,
    QuizSession,
    SessionParticipant,
    SessionStatus,
    User,
)

ROOM_CODE_ALPHABET = string.ascii_uppercase + string.digits
ROOM_CODE_LENGTH = 6
ROOM_CODE_MAX_ATTEMPTS = 5


class SessionQuizNotFoundError(Exception):
    pass


class RoomCodeConflictError(Exception):
    pass


class SessionNotJoinableError(Exception):
    pass


class DuplicateSessionParticipantError(Exception):
    pass


class StartQuestionSessionNotFoundError(Exception):
    pass


class SessionQuestionNotFoundError(Exception):
    pass


class QuestionNotInSessionQuizError(Exception):
    pass


class DuplicateQuestionEventError(Exception):
    pass


class ActiveQuestionConflictError(Exception):
    pass


class StartQuestionSessionEndedError(Exception):
    pass


class AnswerParticipantNotFoundError(Exception):
    pass


class AnswerSessionEndedError(Exception):
    pass


class AnswerQuestionNotFoundError(Exception):
    pass


class AnswerOutsideQuestionWindowError(Exception):
    pass


class InvalidQuestionAnswerSelectionError(Exception):
    pass


class DuplicateQuestionResponseError(Exception):
    pass


def _integrity_constraint_name(error: IntegrityError) -> str | None:
    candidates = (
        error.orig,
        getattr(error.orig, "__cause__", None),
        getattr(error.orig, "__context__", None),
        getattr(error.orig, "diag", None),
    )
    for candidate in candidates:
        constraint_name = getattr(candidate, "constraint_name", None)
        if constraint_name:
            return str(constraint_name)
    return None


def generate_room_code() -> str:
    return "".join(secrets.choice(ROOM_CODE_ALPHABET) for _ in range(ROOM_CODE_LENGTH))


def utc_now() -> datetime:
    return datetime.now(UTC)


async def launch_session(
    session: AsyncSession,
    organizer: User,
    quiz_id: UUID,
    room_code_factory: Callable[[], str] = generate_room_code,
) -> QuizSession:
    result = await session.execute(
        select(Quiz).where(Quiz.id == quiz_id, Quiz.owner_id == organizer.id)
    )
    quiz = result.scalar_one_or_none()
    if quiz is None:
        raise SessionQuizNotFoundError

    last_room_code_error: IntegrityError | None = None
    for _ in range(ROOM_CODE_MAX_ATTEMPTS):
        quiz_session = QuizSession(
            quiz_id=quiz.id,
            organizer_id=organizer.id,
            room_code=room_code_factory(),
            status=SessionStatus.WAITING,
        )
        session.add(quiz_session)

        try:
            await session.commit()
        except IntegrityError as error:
            await session.rollback()
            if _integrity_constraint_name(error) != "uq_sessions_room_code":
                raise
            last_room_code_error = error
            continue

        await session.refresh(quiz_session)
        return quiz_session

    raise RoomCodeConflictError from last_room_code_error


async def join_session(
    session: AsyncSession,
    participant: User,
    room_code: str,
    display_name: str,
) -> SessionParticipant:
    result = await session.execute(
        select(QuizSession).where(QuizSession.room_code == room_code)
    )
    quiz_session = result.scalar_one_or_none()
    if quiz_session is None or quiz_session.status is SessionStatus.ENDED:
        raise SessionNotJoinableError

    existing_result = await session.execute(
        select(SessionParticipant).where(
            SessionParticipant.session_id == quiz_session.id,
            SessionParticipant.user_id == participant.id,
        )
    )
    if existing_result.scalar_one_or_none() is not None:
        raise DuplicateSessionParticipantError

    session_participant = SessionParticipant(
        session_id=quiz_session.id,
        user_id=participant.id,
        display_name=display_name,
    )
    session.add(session_participant)

    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        if (
            _integrity_constraint_name(error)
            == "uq_session_participants_session_id_user_id"
        ):
            raise DuplicateSessionParticipantError from error
        raise

    await session.refresh(session_participant)
    return session_participant


async def start_question(
    session: AsyncSession,
    organizer: User,
    session_id: UUID,
    question_id: UUID,
    now_factory: Callable[[], datetime] = utc_now,
    duration_seconds: int | None = None,
) -> QuestionEvent:
    session_result = await session.execute(
        select(QuizSession).where(
            QuizSession.id == session_id,
            QuizSession.organizer_id == organizer.id,
        )
    )
    quiz_session = session_result.scalar_one_or_none()
    if quiz_session is None:
        raise StartQuestionSessionNotFoundError
    if quiz_session.status is SessionStatus.ENDED:
        raise StartQuestionSessionEndedError

    question_result = await session.execute(select(Question).where(Question.id == question_id))
    question = question_result.scalar_one_or_none()
    if question is None:
        raise SessionQuestionNotFoundError
    if question.quiz_id != quiz_session.quiz_id:
        raise QuestionNotInSessionQuizError

    now = now_factory()
    active_result = await session.execute(
        select(QuestionEvent).where(
            QuestionEvent.session_id == quiz_session.id,
            QuestionEvent.status == QuestionEventStatus.ACTIVE,
        )
    )
    active_event = active_result.scalar_one_or_none()
    if active_event is not None:
        active_event.status = QuestionEventStatus.CLOSED
        active_event.ended_at = now
        await session.flush()

    window_seconds = duration_seconds
    if window_seconds is None:
        window_seconds = 30

    question_event = QuestionEvent(
        session_id=quiz_session.id,
        question_id=question.id,
        status=QuestionEventStatus.ACTIVE,
        started_at=now,
        ended_at=now + timedelta(seconds=window_seconds),
    )
    quiz_session.status = SessionStatus.ACTIVE
    session.add(question_event)

    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        constraint_name = _integrity_constraint_name(error)
        if constraint_name == "uq_question_events_session_id_question_id":
            raise DuplicateQuestionEventError from error
        if constraint_name == "uq_question_events_active_session_id":
            raise ActiveQuestionConflictError from error
        raise

    await session.refresh(question_event)
    return question_event


async def submit_answer(
    session: AsyncSession,
    participant: User,
    session_id: UUID,
    question_id: UUID,
    selected_answer_ids: list[UUID],
    text_answer: str | None,
    now_factory: Callable[[], datetime] = utc_now,
) -> QuestionResponse:
    session_result = await session.execute(select(QuizSession).where(QuizSession.id == session_id))
    quiz_session = session_result.scalar_one_or_none()
    if quiz_session is not None and quiz_session.status is SessionStatus.ENDED:
        raise AnswerSessionEndedError

    participant_result = await session.execute(
        select(SessionParticipant).where(
            SessionParticipant.session_id == session_id,
            SessionParticipant.user_id == participant.id,
        )
    )
    session_participant = participant_result.scalar_one_or_none()
    if session_participant is None:
        raise AnswerParticipantNotFoundError

    event_result = await session.execute(
        select(QuestionEvent).where(
            QuestionEvent.session_id == session_id,
            QuestionEvent.question_id == question_id,
            QuestionEvent.status == QuestionEventStatus.ACTIVE,
        )
    )
    question_event = event_result.scalar_one_or_none()
    if question_event is None:
        raise AnswerQuestionNotFoundError

    now = now_factory()
    if (
        question_event.started_at is None
        or question_event.ended_at is None
        or now < question_event.started_at
        or now > question_event.ended_at
    ):
        raise AnswerOutsideQuestionWindowError

    if not selected_answer_ids:
        raise InvalidQuestionAnswerSelectionError

    question_result = await session.execute(select(Question).where(Question.id == question_id))
    question = question_result.scalar_one_or_none()
    if question is None:
        raise AnswerQuestionNotFoundError

    if question.choice_mode is ChoiceMode.SINGLE and len(selected_answer_ids) != 1:
        raise InvalidQuestionAnswerSelectionError
    if len(set(selected_answer_ids)) != len(selected_answer_ids):
        raise InvalidQuestionAnswerSelectionError

    answers_result = await session.execute(select(Answer).where(Answer.question_id == question_id))
    valid_answer_ids = {answer.id for answer in answers_result.scalars().all()}
    if any(answer_id not in valid_answer_ids for answer_id in selected_answer_ids):
        raise InvalidQuestionAnswerSelectionError

    existing_result = await session.execute(
        select(QuestionResponse).where(
            QuestionResponse.participant_id == session_participant.id,
            QuestionResponse.question_event_id == question_event.id,
        )
    )
    if existing_result.scalar_one_or_none() is not None:
        raise DuplicateQuestionResponseError

    response = QuestionResponse(
        participant_id=session_participant.id,
        question_event_id=question_event.id,
        selected_answer_ids=[str(answer_id) for answer_id in selected_answer_ids],
        text_answer=text_answer,
        meta={},
    )
    session.add(response)

    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        if (
            _integrity_constraint_name(error)
            == "uq_question_responses_participant_id_question_event_id"
        ):
            raise DuplicateQuestionResponseError from error
        raise

    await session.refresh(response)
    return response
