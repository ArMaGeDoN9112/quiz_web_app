import uuid
from datetime import datetime
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import ChoiceMode, QuestionType, QuizStatus


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


class AnswerCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    is_correct: bool = False

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Answer text is required")
        return normalized


class QuestionCreateRequest(BaseModel):
    type: QuestionType
    choice_mode: ChoiceMode
    text: str = Field(min_length=1, max_length=5000)
    image_url: str | None = Field(default=None, max_length=2048)
    points: int = Field(default=1, ge=1, le=1000)
    answers: list[AnswerCreateRequest] = Field(min_length=2, max_length=20)

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Question text is required")
        return normalized

    @field_validator("image_url")
    @classmethod
    def normalize_image_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Image URL cannot be blank")
        parsed_url = urlparse(normalized)
        if (
            parsed_url.scheme not in {"http", "https"}
            or not parsed_url.netloc
            or parsed_url.hostname is None
            or any(character.isspace() for character in normalized)
        ):
            raise ValueError("Image URL must be an http or https URL")
        return normalized

    @model_validator(mode="after")
    def validate_question_mode(self) -> "QuestionCreateRequest":
        correct_count = sum(1 for answer in self.answers if answer.is_correct)

        if self.type is QuestionType.IMAGE and self.image_url is None:
            raise ValueError("Image questions require image_url")
        if self.type is QuestionType.TEXT and self.image_url is not None:
            raise ValueError("Text questions cannot include image_url")
        if self.choice_mode is ChoiceMode.SINGLE and correct_count != 1:
            raise ValueError("Single choice questions require exactly one correct answer")
        if self.choice_mode is ChoiceMode.MULTIPLE and correct_count < 2:
            raise ValueError("Multiple choice questions require at least two correct answers")

        return self


class AnswerResponse(BaseModel):
    id: uuid.UUID
    text: str
    is_correct: bool
    position: int

    model_config = ConfigDict(from_attributes=True)


class QuestionResponse(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    type: QuestionType
    choice_mode: ChoiceMode
    text: str
    image_url: str | None
    points: int
    position: int
    answers: list[AnswerResponse]

    model_config = ConfigDict(from_attributes=True)


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
