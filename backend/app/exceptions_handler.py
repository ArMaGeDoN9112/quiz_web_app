from collections.abc import Callable
import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.services.auth import DuplicateEmailError, InvalidCredentialsError
from app.services.quiz import (
    QuestionNotFoundError,
    QuestionPositionConflictError,
    QuizNotFoundError,
)
from app.services.session import (
    ActiveQuestionConflictError,
    AnswerOutsideQuestionWindowError,
    AnswerParticipantNotFoundError,
    AnswerQuestionNotFoundError,
    AnswerSessionEndedError,
    CurrentQuestionAccessError,
    CurrentQuestionNotFoundError,
    DuplicateQuestionEventError,
    DuplicateQuestionResponseError,
    EndSessionNotFoundError,
    InvalidQuestionAnswerSelectionError,
    ProfileDisplayNameRequiredError,
    QuestionNotInSessionQuizError,
    RoomCodeConflictError,
    SessionContextAccessError,
    SessionContextNotFoundError,
    SessionNotJoinableError,
    SessionQuestionNotFoundError,
    SessionQuizNotFoundError,
    SessionResultAccessError,
    SessionResultNotFoundError,
    SessionScoreboardAccessError,
    SessionScoreboardNotFoundError,
    StartQuestionSessionEndedError,
    StartQuestionSessionNotFoundError,
)

ExceptionHandler = Callable[[Request, Exception], JSONResponse]

logger = logging.getLogger(__name__)


def _handler(status_code: int, detail: str) -> ExceptionHandler:
    async def handler(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": detail})

    return handler


async def unhandled_exception_handler(_: Request, error: Exception) -> JSONResponse:
    logger.exception("Unhandled application exception", exc_info=error)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


duplicate_email_exception_handler = _handler(
    status.HTTP_409_CONFLICT, "Email already registered"
)

EXCEPTION_HANDLERS: dict[type[Exception], ExceptionHandler] = {
    DuplicateEmailError: duplicate_email_exception_handler,
    InvalidCredentialsError: _handler(status.HTTP_401_UNAUTHORIZED, "Invalid email or password"),
    QuizNotFoundError: _handler(status.HTTP_404_NOT_FOUND, "Quiz not found"),
    QuestionNotFoundError: _handler(status.HTTP_404_NOT_FOUND, "Question not found"),
    QuestionPositionConflictError: _handler(
        status.HTTP_409_CONFLICT, "Question position conflict; retry request"
    ),
    SessionContextNotFoundError: _handler(status.HTTP_404_NOT_FOUND, "Session not found"),
    SessionContextAccessError: _handler(status.HTTP_403_FORBIDDEN, "Session access denied"),
    SessionResultNotFoundError: _handler(status.HTTP_404_NOT_FOUND, "Session result not found"),
    SessionResultAccessError: _handler(
        status.HTTP_403_FORBIDDEN, "Session result access denied"
    ),
    SessionQuizNotFoundError: _handler(status.HTTP_404_NOT_FOUND, "Quiz not found"),
    RoomCodeConflictError: _handler(status.HTTP_409_CONFLICT, "Room code conflict; retry request"),
    SessionNotJoinableError: _handler(status.HTTP_404_NOT_FOUND, "Session is not joinable"),
    ProfileDisplayNameRequiredError: _handler(
        status.HTTP_409_CONFLICT, "Profile display name required"
    ),
    StartQuestionSessionNotFoundError: _handler(status.HTTP_404_NOT_FOUND, "Session not found"),
    StartQuestionSessionEndedError: _handler(status.HTTP_409_CONFLICT, "Session is ended"),
    SessionQuestionNotFoundError: _handler(status.HTTP_404_NOT_FOUND, "Question not found"),
    QuestionNotInSessionQuizError: _handler(
        status.HTTP_409_CONFLICT, "Question does not belong to session quiz"
    ),
    DuplicateQuestionEventError: _handler(
        status.HTTP_409_CONFLICT, "Question already used in session"
    ),
    ActiveQuestionConflictError: _handler(
        status.HTTP_409_CONFLICT, "Active question conflict; retry request"
    ),
    CurrentQuestionNotFoundError: _handler(status.HTTP_404_NOT_FOUND, "No active question"),
    CurrentQuestionAccessError: _handler(status.HTTP_403_FORBIDDEN, "Session access denied"),
    AnswerParticipantNotFoundError: _handler(
        status.HTTP_404_NOT_FOUND, "Participant session not found"
    ),
    AnswerSessionEndedError: _handler(status.HTTP_409_CONFLICT, "Session is ended"),
    AnswerQuestionNotFoundError: _handler(status.HTTP_404_NOT_FOUND, "Active question not found"),
    AnswerOutsideQuestionWindowError: _handler(
        status.HTTP_409_CONFLICT, "Question is not accepting answers"
    ),
    InvalidQuestionAnswerSelectionError: _handler(
        status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid answer selection"
    ),
    DuplicateQuestionResponseError: _handler(
        status.HTTP_409_CONFLICT, "Question already answered"
    ),
    SessionScoreboardNotFoundError: _handler(status.HTTP_404_NOT_FOUND, "Session not found"),
    SessionScoreboardAccessError: _handler(
        status.HTTP_403_FORBIDDEN, "Session access denied"
    ),
    EndSessionNotFoundError: _handler(status.HTTP_404_NOT_FOUND, "Session not found"),
}


def register_exception_handlers(app: FastAPI) -> None:
    for exception_class, handler in EXCEPTION_HANDLERS.items():
        app.add_exception_handler(exception_class, handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
