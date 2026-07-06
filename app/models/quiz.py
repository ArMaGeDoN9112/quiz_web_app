import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class QuizStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class QuestionType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"


class ChoiceMode(str, enum.Enum):
    SINGLE = "single"
    MULTIPLE = "multiple"


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("name", name="uq_categories_name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    questions: Mapped[list["Question"]] = relationship(back_populates="category")


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_quizzes_owner_id_users", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[QuizStatus] = mapped_column(
        Enum(
            QuizStatus,
            name="quiz_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda status_enum: [status.value for status in status_enum],
        ),
        nullable=False,
        default=QuizStatus.DRAFT,
        server_default=QuizStatus.DRAFT.value,
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, server_default=text("'{}'::json")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    questions: Mapped[list["Question"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan"
    )


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        UniqueConstraint(
            "quiz_id",
            "position",
            name="uq_questions_quiz_id_position",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quizzes.id", name="fk_questions_quiz_id_quizzes", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "categories.id",
            name="fk_questions_category_id_categories",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    type: Mapped[QuestionType] = mapped_column(
        Enum(
            QuestionType,
            name="question_type",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda type_enum: [question_type.value for question_type in type_enum],
        ),
        nullable=False,
    )
    choice_mode: Mapped[ChoiceMode] = mapped_column(
        Enum(
            ChoiceMode,
            name="choice_mode",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda mode_enum: [mode.value for mode in mode_enum],
        ),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    quiz: Mapped[Quiz] = relationship(back_populates="questions")
    category: Mapped[Category | None] = relationship(back_populates="questions")
    answers: Mapped[list["Answer"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "questions.id", name="fk_answers_question_id_questions", ondelete="CASCADE"
        ),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    question: Mapped[Question] = relationship(back_populates="answers")
