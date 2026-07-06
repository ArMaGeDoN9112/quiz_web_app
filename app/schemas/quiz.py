import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import QuizStatus


class QuizCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Quiz title is required")
        return normalized


class QuizUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: QuizStatus | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_null_non_nullable_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for field_name in ("title", "status"):
                if field_name in data and data[field_name] is None:
                    raise ValueError(f"{field_name} cannot be null")
        return data

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Quiz title is required")
        return normalized


class QuizResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    description: str | None
    status: QuizStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
