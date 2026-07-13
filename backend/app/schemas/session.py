import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import QuestionEventStatus, SessionStatus


class SessionLaunchRequest(BaseModel):
    quiz_id: uuid.UUID


class SessionJoinRequest(BaseModel):
    room_code: str = Field(min_length=1, max_length=16)
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator("room_code")
    @classmethod
    def normalize_room_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Room code is required")
        return normalized

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Display name is required")
        return normalized


class SessionResponse(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    organizer_id: uuid.UUID
    room_code: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    ended_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SessionParticipantResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StartQuestionRequest(BaseModel):
    question_id: uuid.UUID
    duration_seconds: int | None = Field(default=None, ge=1, le=3600)


class QuestionEventResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    question_id: uuid.UUID
    status: QuestionEventStatus
    started_at: datetime | None
    ended_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SubmitAnswerRequest(BaseModel):
    question_id: uuid.UUID
    selected_answer_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    text_answer: str | None = Field(default=None, max_length=2000)

    @field_validator("text_answer")
    @classmethod
    def normalize_text_answer(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Text answer cannot be blank")
        return normalized


class QuestionAnswerResponse(BaseModel):
    id: uuid.UUID
    participant_id: uuid.UUID
    question_event_id: uuid.UUID
    selected_answer_ids: list[str]
    text_answer: str | None
    awarded_points: int
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScoreboardEntryResponse(BaseModel):
    participant_id: uuid.UUID
    display_name: str
    score: int
    rank: int


class SessionScoreboardResponse(BaseModel):
    session_id: uuid.UUID
    status: SessionStatus
    entries: list[ScoreboardEntryResponse]
    winner_ids: list[uuid.UUID]
