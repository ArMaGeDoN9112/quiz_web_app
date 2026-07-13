from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Answer, Question, Quiz, QuizStatus, User
from app.schemas.quiz import (
    QuestionCreateRequest,
    QuizCreateRequest,
    QuizSettings,
    QuizUpdateRequest,
)


class QuizNotFoundError(Exception):
    pass


class QuestionPositionConflictError(Exception):
    pass


class QuestionNotFoundError(Exception):
    pass


class QuizService:
    def __init__(self, session: AsyncSession, owner: User) -> None:
        self.session = session
        self.owner = owner

    async def create(self, data: QuizCreateRequest) -> Quiz:
        quiz = Quiz(
            owner_id=self.owner.id,
            title=data.title,
            description=data.description,
            status=QuizStatus.DRAFT,
            settings=data.settings.model_dump(),
        )
        self.session.add(quiz)

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise

        await self.session.refresh(quiz)
        return quiz

    async def list(self) -> list[Quiz]:
        result = await self.session.execute(
            select(Quiz)
            .where(Quiz.owner_id == self.owner.id)
            .order_by(Quiz.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, quiz_id: UUID) -> Quiz:
        result = await self.session.execute(
            select(Quiz).where(Quiz.id == quiz_id, Quiz.owner_id == self.owner.id)
        )
        quiz = result.scalar_one_or_none()
        if quiz is None:
            raise QuizNotFoundError
        return quiz

    async def update(self, quiz_id: UUID, data: QuizUpdateRequest) -> Quiz:
        quiz = await self.get(quiz_id)
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field == "settings":
                quiz.settings = self._merge_settings(quiz.settings, value)
                continue
            setattr(quiz, field, value)

        await self.session.commit()
        await self.session.refresh(quiz)
        return quiz

    async def delete(self, quiz_id: UUID) -> None:
        quiz = await self.get(quiz_id)
        await self.session.delete(quiz)
        await self.session.commit()

    async def create_question(self, quiz_id: UUID, data: QuestionCreateRequest) -> Question:
        await self.get(quiz_id)
        position = await self._next_question_position(quiz_id)
        question = Question(
            quiz_id=quiz_id,
            type=data.type,
            choice_mode=data.choice_mode,
            text=data.text,
            image_url=data.image_url,
            points=data.points,
            duration_seconds=data.duration_seconds,
            position=position,
            answers=[
                Answer(
                    text=answer.text,
                    is_correct=answer.is_correct,
                    position=index,
                )
                for index, answer in enumerate(data.answers, start=1)
            ],
        )
        self.session.add(question)
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise QuestionPositionConflictError from error
        await self.session.refresh(question, attribute_names=["answers"])
        return question

    async def list_questions(self, quiz_id: UUID) -> list[Question]:
        await self.get(quiz_id)
        result = await self.session.execute(
            select(Question)
            .where(Question.quiz_id == quiz_id)
            .options(selectinload(Question.answers))
            .order_by(Question.position)
        )
        return list(result.scalars().all())

    async def update_question(
        self,
        quiz_id: UUID,
        question_id: UUID,
        data: QuestionCreateRequest,
    ) -> Question:
        await self.get(quiz_id)
        result = await self.session.execute(
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
            Answer(
                text=answer.text,
                is_correct=answer.is_correct,
                position=index,
            )
            for index, answer in enumerate(data.answers, start=1)
        ]
        await self.session.commit()
        await self.session.refresh(question, attribute_names=["answers"])
        return question

    async def _next_question_position(self, quiz_id: UUID) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.max(Question.position), 0)).where(
                Question.quiz_id == quiz_id
            )
        )
        return int(result.scalar_one()) + 1

    def _merge_settings(
        self,
        current_settings: dict[str, object],
        changes: dict[str, object],
    ) -> dict[str, object]:
        settings = QuizSettings.model_validate(current_settings).model_dump()
        settings.update(changes)
        return QuizSettings.model_validate(settings).model_dump()


async def create_quiz(
    session: AsyncSession,
    owner: User,
    data: QuizCreateRequest,
) -> Quiz:
    return await QuizService(session, owner).create(data)


async def list_quizzes(session: AsyncSession, owner: User) -> list[Quiz]:
    return await QuizService(session, owner).list()


async def get_quiz(session: AsyncSession, owner: User, quiz_id: UUID) -> Quiz:
    return await QuizService(session, owner).get(quiz_id)


async def update_quiz(
    session: AsyncSession,
    owner: User,
    quiz_id: UUID,
    data: QuizUpdateRequest,
) -> Quiz:
    return await QuizService(session, owner).update(quiz_id, data)


async def delete_quiz(session: AsyncSession, owner: User, quiz_id: UUID) -> None:
    await QuizService(session, owner).delete(quiz_id)


async def create_question(
    session: AsyncSession,
    owner: User,
    quiz_id: UUID,
    data: QuestionCreateRequest,
) -> Question:
    return await QuizService(session, owner).create_question(quiz_id, data)


async def update_question(
    session: AsyncSession,
    owner: User,
    quiz_id: UUID,
    question_id: UUID,
    data: QuestionCreateRequest,
) -> Question:
    return await QuizService(session, owner).update_question(quiz_id, question_id, data)


async def list_questions(session: AsyncSession, owner: User, quiz_id: UUID) -> list[Question]:
    return await QuizService(session, owner).list_questions(quiz_id)
