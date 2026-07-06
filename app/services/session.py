import secrets
import string
from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Quiz, QuizSession, SessionStatus, User

ROOM_CODE_ALPHABET = string.ascii_uppercase + string.digits
ROOM_CODE_LENGTH = 6
ROOM_CODE_MAX_ATTEMPTS = 5


class SessionQuizNotFoundError(Exception):
    pass


class RoomCodeConflictError(Exception):
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
