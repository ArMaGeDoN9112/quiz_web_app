from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Quiz, QuizStatus, User
from app.schemas.quiz import QuizCreateRequest, QuizSettings, QuizUpdateRequest


class QuizNotFoundError(Exception):
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
