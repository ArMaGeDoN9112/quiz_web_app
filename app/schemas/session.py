import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import SessionStatus


class SessionLaunchRequest(BaseModel):
    quiz_id: uuid.UUID


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
