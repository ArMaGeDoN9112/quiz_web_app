import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SessionStatus(str, enum.Enum):
    WAITING = "waiting"
    ACTIVE = "active"
    ENDED = "ended"


class QuestionEventStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    CLOSED = "closed"


class QuizSession(Base):
    __tablename__ = "sessions"
    __table_args__ = (UniqueConstraint("room_code", name="uq_sessions_room_code"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quizzes.id", name="fk_sessions_quiz_id_quizzes", ondelete="CASCADE"),
        nullable=False,
    )
    organizer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_sessions_organizer_id_users", ondelete="CASCADE"),
        nullable=False,
    )
    room_code: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(
            SessionStatus,
            name="session_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda status_enum: [status.value for status in status_enum],
        ),
        nullable=False,
        default=SessionStatus.WAITING,
        server_default=SessionStatus.WAITING.value,
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
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    participants: Mapped[list["SessionParticipant"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    question_events: Mapped[list["QuestionEvent"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class SessionParticipant(Base):
    __tablename__ = "session_participants"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "user_id",
            name="uq_session_participants_session_id_user_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "sessions.id",
            name="fk_session_participants_session_id_sessions",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_session_participants_user_id_users",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    session: Mapped[QuizSession] = relationship(back_populates="participants")
    responses: Mapped[list["QuestionResponse"]] = relationship(
        back_populates="participant", cascade="all, delete-orphan"
    )


class QuestionEvent(Base):
    __tablename__ = "question_events"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "question_id",
            name="uq_question_events_session_id_question_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", name="fk_question_events_session_id_sessions", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", name="fk_question_events_question_id_questions", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[QuestionEventStatus] = mapped_column(
        Enum(
            QuestionEventStatus,
            name="question_event_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda status_enum: [status.value for status in status_enum],
        ),
        nullable=False,
        default=QuestionEventStatus.SCHEDULED,
        server_default=QuestionEventStatus.SCHEDULED.value,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[QuizSession] = relationship(back_populates="question_events")
    responses: Mapped[list["QuestionResponse"]] = relationship(
        back_populates="question_event", cascade="all, delete-orphan"
    )


class QuestionResponse(Base):
    __tablename__ = "question_responses"
    __table_args__ = (
        UniqueConstraint(
            "participant_id",
            "question_event_id",
            name="uq_question_responses_participant_id_question_event_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "session_participants.id",
            name="fk_question_responses_participant_id_session_participants",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    question_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "question_events.id",
            name="fk_question_responses_question_event_id_question_events",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    selected_answer_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    text_answer: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    participant: Mapped[SessionParticipant] = relationship(back_populates="responses")
    question_event: Mapped[QuestionEvent] = relationship(back_populates="responses")
