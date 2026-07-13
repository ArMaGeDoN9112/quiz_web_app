import secrets
import string
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
from app.services.scoring import ScoreCandidate, rank_scoreboard, score_selected_answers

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


class ProfileDisplayNameRequiredError(Exception):
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


class SessionScoreboardNotFoundError(Exception):
    pass


class SessionScoreboardAccessError(Exception):
    pass


class CurrentQuestionNotFoundError(Exception):
    pass


class CurrentQuestionAccessError(Exception):
    pass


class EndSessionNotFoundError(Exception):
    pass


class SessionResultNotFoundError(Exception):
    pass


class SessionResultAccessError(Exception):
    pass


@dataclass(frozen=True)
class SessionScoreboard:
    session_id: UUID
    status: SessionStatus
    entries: list[dict[str, object]]
    winner_ids: list[UUID]


def _final_result_entries(quiz_session: QuizSession) -> list[dict[str, object]]:
    final_results = quiz_session.final_results or {}
    entries = final_results.get("entries", [])
    return entries if isinstance(entries, list) else []


def _final_winner_ids(quiz_session: QuizSession) -> list[str]:
    final_results = quiz_session.final_results or {}
    winner_ids = final_results.get("winner_ids", [])
    return winner_ids if isinstance(winner_ids, list) else []


async def get_participant_session_history(
    session: AsyncSession,
    participant: User,
) -> list[dict[str, object]]:
    result = await session.execute(
        select(SessionParticipant, QuizSession, Quiz)
        .join(QuizSession, SessionParticipant.session_id == QuizSession.id)
        .join(Quiz, QuizSession.quiz_id == Quiz.id)
        .where(
            SessionParticipant.user_id == participant.id,
            QuizSession.status == SessionStatus.ENDED,
        )
        .order_by(QuizSession.ended_at.desc(), QuizSession.id)
    )
    history: list[dict[str, object]] = []
    for session_participant, quiz_session, quiz in result.all():
        entries = _final_result_entries(quiz_session)
        entry = next(
            (item for item in entries if item.get("participant_id") == str(session_participant.id)),
            None,
        )
        if entry is None or quiz_session.ended_at is None:
            continue
        history.append(
            {
                "session_id": quiz_session.id,
                "quiz_id": quiz.id,
                "quiz_title": quiz.title,
                "ended_at": quiz_session.ended_at,
                "score": entry["score"],
                "rank": entry["rank"],
                "participant_count": len(entries),
            }
        )
    return history


async def get_organizer_session_history(
    session: AsyncSession,
    organizer: User,
) -> list[dict[str, object]]:
    result = await session.execute(
        select(QuizSession, Quiz)
        .join(Quiz, QuizSession.quiz_id == Quiz.id)
        .where(
            QuizSession.organizer_id == organizer.id,
            QuizSession.status == SessionStatus.ENDED,
        )
        .order_by(QuizSession.ended_at.desc(), QuizSession.id)
    )
    history: list[dict[str, object]] = []
    for quiz_session, quiz in result.all():
        entries = _final_result_entries(quiz_session)
        winner_ids = set(_final_winner_ids(quiz_session))
        if quiz_session.ended_at is None:
            continue
        history.append(
            {
                "session_id": quiz_session.id,
                "quiz_id": quiz.id,
                "quiz_title": quiz.title,
                "ended_at": quiz_session.ended_at,
                "participant_count": len(entries),
                "winner_names": [
                    str(entry["display_name"])
                    for entry in entries
                    if entry.get("participant_id") in winner_ids
                ],
            }
        )
    return history


async def get_session_result(
    session: AsyncSession,
    current_user: User,
    session_id: UUID,
) -> dict[str, object]:
    result = await session.execute(
        select(QuizSession, Quiz)
        .join(Quiz, QuizSession.quiz_id == Quiz.id)
        .where(QuizSession.id == session_id, QuizSession.status == SessionStatus.ENDED)
    )
    row = result.all()
    if not row:
        raise SessionResultNotFoundError
    quiz_session, quiz = row[0]

    if current_user.id != quiz_session.organizer_id:
        participant_result = await session.execute(
            select(SessionParticipant).where(
                SessionParticipant.session_id == quiz_session.id,
                SessionParticipant.user_id == current_user.id,
            )
        )
        if participant_result.scalar_one_or_none() is None:
            raise SessionResultAccessError

    entries = _final_result_entries(quiz_session)
    if quiz_session.ended_at is None:
        raise SessionResultNotFoundError
    return {
        "session_id": quiz_session.id,
        "quiz_id": quiz.id,
        "quiz_title": quiz.title,
        "organizer_id": quiz_session.organizer_id,
        "ended_at": quiz_session.ended_at,
        "participant_count": len(entries),
        "entries": entries,
        "winner_ids": _final_winner_ids(quiz_session),
    }


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
) -> SessionParticipant:
    if participant.display_name is None:
        raise ProfileDisplayNameRequiredError

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
        display_name=participant.display_name,
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

    question_event = QuestionEvent(
        session_id=quiz_session.id,
        question_id=question.id,
        status=QuestionEventStatus.ACTIVE,
        started_at=now,
        ended_at=(
            now + timedelta(seconds=duration_seconds)
            if duration_seconds is not None
            else None
        ),
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
        or now < question_event.started_at
        or (
            question_event.ended_at is not None
            and now > question_event.ended_at
        )
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
    answers = answers_result.scalars().all()
    valid_answer_ids = {answer.id for answer in answers}
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
        awarded_points=score_selected_answers(
            selected_answer_ids=selected_answer_ids,
            correct_answer_ids={answer.id for answer in answers if answer.is_correct},
            question_points=question.points,
        ),
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


async def get_current_question(
    session: AsyncSession,
    current_user: User,
    session_id: UUID,
) -> dict[str, object]:
    session_result = await session.execute(select(QuizSession).where(QuizSession.id == session_id))
    quiz_session = session_result.scalar_one_or_none()
    if quiz_session is None:
        raise CurrentQuestionNotFoundError

    if current_user.id != quiz_session.organizer_id:
        participant_result = await session.execute(
            select(SessionParticipant).where(
                SessionParticipant.session_id == session_id,
                SessionParticipant.user_id == current_user.id,
            )
        )
        if participant_result.scalar_one_or_none() is None:
            raise CurrentQuestionAccessError

    event_result = await session.execute(
        select(QuestionEvent).where(
            QuestionEvent.session_id == session_id,
            QuestionEvent.status == QuestionEventStatus.ACTIVE,
        )
    )
    question_event = event_result.scalar_one_or_none()
    if question_event is None:
        raise CurrentQuestionNotFoundError

    question_result = await session.execute(
        select(Question)
        .where(Question.id == question_event.question_id)
        .options(selectinload(Question.answers))
    )
    question = question_result.scalar_one_or_none()
    if question is None:
        raise CurrentQuestionNotFoundError

    return {
        "event_id": question_event.id,
        "session_id": quiz_session.id,
        "question_id": question.id,
        "type": question.type,
        "choice_mode": question.choice_mode,
        "text": question.text,
        "image_url": question.image_url,
        "ends_at": question_event.ended_at,
        "answers": [
            {"id": answer.id, "text": answer.text, "position": answer.position}
            for answer in question.answers
        ],
    }


async def get_session_scoreboard(
    session: AsyncSession,
    current_user: User,
    session_id: UUID,
) -> SessionScoreboard:
    session_result = await session.execute(select(QuizSession).where(QuizSession.id == session_id))
    quiz_session = session_result.scalar_one_or_none()
    if quiz_session is None:
        raise SessionScoreboardNotFoundError

    if current_user.id != quiz_session.organizer_id:
        participant_result = await session.execute(
            select(SessionParticipant).where(
                SessionParticipant.session_id == session_id,
                SessionParticipant.user_id == current_user.id,
            )
        )
        if participant_result.scalar_one_or_none() is None:
            raise SessionScoreboardAccessError

    participants_result = await session.execute(
        select(SessionParticipant)
        .where(SessionParticipant.session_id == session_id)
        .order_by(SessionParticipant.joined_at, SessionParticipant.id)
    )
    participants = participants_result.scalars().all()
    responses_result = await session.execute(
        select(QuestionResponse)
        .join(QuestionEvent)
        .where(QuestionEvent.session_id == session_id)
    )
    responses = responses_result.scalars().all()

    score_by_participant = {participant.id: 0 for participant in participants}
    for response in responses:
        score_by_participant[response.participant_id] = (
            score_by_participant.get(response.participant_id, 0) + response.awarded_points
        )

    ranked_entries, winner_ids = rank_scoreboard(
        [
            ScoreCandidate(
                participant_id=participant.id,
                display_name=participant.display_name,
                joined_order=index,
                score=score_by_participant[participant.id],
            )
            for index, participant in enumerate(participants, start=1)
        ]
    )
    return SessionScoreboard(
        session_id=quiz_session.id,
        status=quiz_session.status,
        entries=[
            {
                "participant_id": entry.participant_id,
                "display_name": entry.display_name,
                "score": entry.score,
                "rank": entry.rank,
            }
            for entry in ranked_entries
        ],
        winner_ids=winner_ids,
    )


async def end_session(
    session: AsyncSession,
    organizer: User,
    session_id: UUID,
    now_factory: Callable[[], datetime] = utc_now,
) -> SessionScoreboard:
    session_result = await session.execute(
        select(QuizSession).where(
            QuizSession.id == session_id,
            QuizSession.organizer_id == organizer.id,
        )
    )
    quiz_session = session_result.scalar_one_or_none()
    if quiz_session is None:
        raise EndSessionNotFoundError

    now = now_factory()
    active_result = await session.execute(
        select(QuestionEvent).where(
            QuestionEvent.session_id == session_id,
            QuestionEvent.status == QuestionEventStatus.ACTIVE,
        )
    )
    active_event = active_result.scalar_one_or_none()
    if active_event is not None:
        active_event.status = QuestionEventStatus.CLOSED
        active_event.ended_at = now

    scoreboard = await get_session_scoreboard(session, organizer, session_id)
    quiz_session.status = SessionStatus.ENDED
    quiz_session.ended_at = now
    quiz_session.final_results = {
        "entries": [
            {
                **entry,
                "participant_id": str(entry["participant_id"]),
            }
            for entry in scoreboard.entries
        ],
        "winner_ids": [str(winner_id) for winner_id in scoreboard.winner_ids],
    }
    await session.commit()
    await session.refresh(quiz_session)
    return SessionScoreboard(
        session_id=scoreboard.session_id,
        status=SessionStatus.ENDED,
        entries=scoreboard.entries,
        winner_ids=scoreboard.winner_ids,
    )
