from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.errors import integrity_constraint_name
from app.models import Answer, Question, Quiz, QuizStatus, User
from app.schemas.quiz import QuestionCreateRequest, QuizCreateRequest, QuizSettings, QuizUpdateRequest


class QuizNotFoundError(Exception):
    pass


class QuestionPositionConflictError(Exception):
    pass


class QuestionNotFoundError(Exception):
    pass


async def create_quiz(session: AsyncSession, owner: User, data: QuizCreateRequest) -> Quiz:
    quiz = Quiz(
        owner_id=owner.id,
        title=data.title,
        description=data.description,
        status=QuizStatus.DRAFT,
        settings=data.settings.model_dump(),
    )
    session.add(quiz)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(quiz)
    return quiz


async def list_quizzes(
    session: AsyncSession, owner: User, limit: int = 20, offset: int = 0
) -> list[Quiz]:
    result = await session.execute(
        select(Quiz)
        .where(Quiz.owner_id == owner.id)
        .order_by(Quiz.created_at.desc(), Quiz.id)
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_quiz(session: AsyncSession, owner: User, quiz_id: UUID) -> Quiz:
    result = await session.execute(select(Quiz).where(Quiz.id == quiz_id, Quiz.owner_id == owner.id))
    quiz = result.scalar_one_or_none()
    if quiz is None:
        raise QuizNotFoundError
    return quiz


async def update_quiz(
    session: AsyncSession, owner: User, quiz_id: UUID, data: QuizUpdateRequest
) -> Quiz:
    quiz = await get_quiz(session, owner, quiz_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "settings":
            settings = QuizSettings.model_validate(quiz.settings).model_dump()
            settings.update(value)
            quiz.settings = QuizSettings.model_validate(settings).model_dump()
        else:
            setattr(quiz, field, value)
    await session.commit()
    await session.refresh(quiz)
    return quiz


async def delete_quiz(session: AsyncSession, owner: User, quiz_id: UUID) -> None:
    await session.delete(await get_quiz(session, owner, quiz_id))
    await session.commit()


async def create_question(
    session: AsyncSession, owner: User, quiz_id: UUID, data: QuestionCreateRequest
) -> Question:
    await get_quiz(session, owner, quiz_id)
    position_result = await session.execute(
        select(func.coalesce(func.max(Question.position), 0)).where(Question.quiz_id == quiz_id)
    )
    question = Question(
        quiz_id=quiz_id,
        type=data.type,
        choice_mode=data.choice_mode,
        text=data.text,
        image_url=data.image_url,
        points=data.points,
        duration_seconds=data.duration_seconds,
        position=int(position_result.scalar_one()) + 1,
        answers=[
            Answer(text=answer.text, is_correct=answer.is_correct, position=index)
            for index, answer in enumerate(data.answers, start=1)
        ],
    )
    session.add(question)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        if integrity_constraint_name(error) == "uq_questions_quiz_id_position":
            raise QuestionPositionConflictError from error
        raise
    await session.refresh(question, attribute_names=["answers"])
    return question


async def list_questions(
    session: AsyncSession, owner: User, quiz_id: UUID, limit: int = 20, offset: int = 0
) -> list[Question]:
    await get_quiz(session, owner, quiz_id)
    result = await session.execute(
        select(Question)
        .where(Question.quiz_id == quiz_id)
        .options(selectinload(Question.answers))
        .order_by(Question.position)
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def update_question(
    session: AsyncSession,
    owner: User,
    quiz_id: UUID,
    question_id: UUID,
    data: QuestionCreateRequest,
) -> Question:
    await get_quiz(session, owner, quiz_id)
    result = await session.execute(
        select(Question)
        .where(Question.id == question_id, Question.quiz_id == quiz_id)
        .options(selectinload(Question.answers))
    )
    question = result.scalar_one_or_none()
    if question is None:
        raise QuestionNotFoundError
    question.type = data.type
    question.choice_mode = data.choice_mode
    question.text = data.text
    question.image_url = data.image_url
    question.points = data.points
    question.duration_seconds = data.duration_seconds
    question.answers = [
        Answer(text=answer.text, is_correct=answer.is_correct, position=index)
        for index, answer in enumerate(data.answers, start=1)
    ]
    await session.commit()
    await session.refresh(question, attribute_names=["answers"])
    return question
