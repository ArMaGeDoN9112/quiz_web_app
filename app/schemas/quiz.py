import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import QuizStatus


class QuizSettings(BaseModel):
    time_limit_seconds: int = Field(default=30, ge=5, le=3600)
    shuffle_questions: bool = False
    shuffle_answers: bool = False
    show_correct_answers: bool = True
    scoring_mode: Literal["standard", "speed_bonus"] = "standard"


class QuizSettingsUpdate(BaseModel):
    time_limit_seconds: int | None = Field(default=None, ge=5, le=3600)
    shuffle_questions: bool | None = None
    shuffle_answers: bool | None = None
    show_correct_answers: bool | None = None
    scoring_mode: Literal["standard", "speed_bonus"] | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_null_settings_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for field_name, value in data.items():
                if value is None:
                    raise ValueError(f"{field_name} cannot be null")
        return data


class QuizCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    settings: QuizSettings = Field(default_factory=QuizSettings)

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
    settings: QuizSettingsUpdate | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_null_non_nullable_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for field_name in ("title", "status", "settings"):
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
    settings: QuizSettings
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
