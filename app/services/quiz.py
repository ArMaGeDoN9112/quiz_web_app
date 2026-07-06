from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Quiz, QuizStatus, User
from app.schemas.quiz import QuizCreateRequest, QuizUpdateRequest


class QuizNotFoundError(Exception):
    pass


async def create_quiz(
    session: AsyncSession,
    owner: User,
    data: QuizCreateRequest,
) -> Quiz:
    quiz = Quiz(
        owner_id=owner.id,
        title=data.title,
        description=data.description,
        status=QuizStatus.DRAFT,
        settings={},
    )
    session.add(quiz)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise

    await session.refresh(quiz)
    return quiz


async def list_quizzes(session: AsyncSession, owner: User) -> list[Quiz]:
    result = await session.execute(
        select(Quiz).where(Quiz.owner_id == owner.id).order_by(Quiz.created_at.desc())
    )
    return list(result.scalars().all())


async def get_quiz(session: AsyncSession, owner: User, quiz_id: UUID) -> Quiz:
    result = await session.execute(
        select(Quiz).where(Quiz.id == quiz_id, Quiz.owner_id == owner.id)
    )
    quiz = result.scalar_one_or_none()
    if quiz is None:
        raise QuizNotFoundError
    return quiz


async def update_quiz(
    session: AsyncSession,
    owner: User,
    quiz_id: UUID,
    data: QuizUpdateRequest,
) -> Quiz:
    quiz = await get_quiz(session, owner, quiz_id)
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(quiz, field, value)

    await session.commit()
    await session.refresh(quiz)
    return quiz


async def delete_quiz(session: AsyncSession, owner: User, quiz_id: UUID) -> None:
    quiz = await get_quiz(session, owner, quiz_id)
    await session.delete(quiz)
    await session.commit()
