import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import ChoiceMode, QuestionType, SessionStatus


class _OrmResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SessionLaunchRequest(BaseModel):
    quiz_id: uuid.UUID


class SessionJoinRequest(BaseModel):
    room_code: str = Field(min_length=1, max_length=16)

    @field_validator("room_code")
    @classmethod
    def normalize_room_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Room code is required")
        return normalized


class SessionResponse(_OrmResponse):
    id: uuid.UUID
    quiz_id: uuid.UUID
    organizer_id: uuid.UUID
    room_code: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    ended_at: datetime | None


class SessionParticipantResponse(_OrmResponse):
    id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    joined_at: datetime


class SessionContextResponse(_OrmResponse):
    session: SessionResponse
    participant: SessionParticipantResponse | None


class PublicAnswerResponse(_OrmResponse):
    id: uuid.UUID
    text: str
    position: int


class CurrentQuestionResponse(_OrmResponse):
    event_id: uuid.UUID
    session_id: uuid.UUID
    question_id: uuid.UUID
    type: QuestionType
    choice_mode: ChoiceMode
    text: str
    image_url: str | None
    ends_at: datetime | None
    shuffle_answers: bool
    answers: list[PublicAnswerResponse]


class ScoreboardEntryResponse(_OrmResponse):
    participant_id: uuid.UUID
    display_name: str
    score: int
    rank: int


class SessionScoreboardResponse(_OrmResponse):
    session_id: uuid.UUID
    status: SessionStatus
    entries: list[ScoreboardEntryResponse]
    winner_ids: list[uuid.UUID]


class SessionLiveUpdateResponse(BaseModel):
    scoreboard: SessionScoreboardResponse
    current_question: CurrentQuestionResponse | None


class WebSocketCommand(BaseModel):
    request_id: uuid.UUID


class StartQuestionCommand(WebSocketCommand):
    type: Literal["question.start"]
    question_id: uuid.UUID
    duration_seconds: int | None = Field(default=None, ge=1, le=3600)


class SubmitAnswerCommand(WebSocketCommand):
    type: Literal["answer.submit"]
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


class EndSessionCommand(WebSocketCommand):
    type: Literal["session.end"]


class ParticipantSessionHistoryResponse(_OrmResponse):
    session_id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_title: str
    ended_at: datetime
    score: int
    rank: int
    participant_count: int


class OrganizerSessionHistoryResponse(_OrmResponse):
    session_id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_title: str
    ended_at: datetime
    participant_count: int
    winner_names: list[str]


class SessionResultResponse(_OrmResponse):
    session_id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_title: str
    organizer_id: uuid.UUID
    ended_at: datetime
    participant_count: int
    entries: list[ScoreboardEntryResponse]
    winner_ids: list[uuid.UUID]
