import secrets
from collections.abc import Callable, Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Question, QuestionEvent, QuestionEventStatus, Quiz, QuizSession, SessionStatus, User
from app.services.session import end_session, start_question, utc_now


def select_next_automatic_question(
    questions: Sequence[Question],
    *,
    used_question_ids: set[UUID],
    shuffle_questions: bool,
    choice: Callable[[Sequence[Question]], Question] = secrets.choice,
) -> Question | None:
    candidates = sorted(
        (question for question in questions if question.id not in used_question_ids),
        key=lambda question: (question.position, question.id),
    )
    if not candidates:
        return None
    return choice(candidates) if shuffle_questions else candidates[0]


async def advance_automatic_session(
    session: AsyncSession,
    session_id: UUID,
    *,
    now_factory: Callable[[], datetime] = utc_now,
) -> bool:
    session_result = await session.execute(
        select(QuizSession)
        .where(QuizSession.id == session_id, QuizSession.status == SessionStatus.ACTIVE)
        .with_for_update(skip_locked=True)
    )
    quiz_session = session_result.scalar_one_or_none()
    if quiz_session is None:
        return False

    quiz_result = await session.execute(select(Quiz).where(Quiz.id == quiz_session.quiz_id))
    quiz = quiz_result.scalar_one_or_none()
    if quiz is None or quiz.settings.get("playback_mode") != "automatic":
        return False

    active_event_result = await session.execute(
        select(QuestionEvent).where(
            QuestionEvent.session_id == session_id,
            QuestionEvent.status == QuestionEventStatus.ACTIVE,
        )
    )
    active_event = active_event_result.scalar_one_or_none()
    now = now_factory()
    if active_event is None or active_event.ended_at is None or active_event.ended_at > now:
        return False

    questions_result = await session.execute(
        select(Question).where(Question.quiz_id == quiz_session.quiz_id)
    )
    questions = questions_result.scalars().all()
    used_question_ids_result = await session.execute(
        select(QuestionEvent.question_id).where(QuestionEvent.session_id == session_id)
    )
    used_question_ids = set(used_question_ids_result.scalars().all())
    next_question = select_next_automatic_question(
        questions,
        used_question_ids=used_question_ids,
        shuffle_questions=bool(quiz.settings.get("shuffle_questions", False)),
    )

    organizer_result = await session.execute(select(User).where(User.id == quiz_session.organizer_id))
    organizer = organizer_result.scalar_one_or_none()
    if organizer is None:
        return False

    if next_question is None:
        await end_session(session, organizer, session_id, now_factory=lambda: now)
        return True

    await start_question(
        session,
        organizer,
        session_id,
        next_question.id,
        now_factory=lambda: now,
        duration_seconds=next_question.duration_seconds,
    )
    return True
