import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import SessionStatus


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
