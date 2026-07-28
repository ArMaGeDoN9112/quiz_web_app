from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole
from app.schemas.session import (
    EndSessionCommand,
    StartQuestionCommand,
    SubmitAnswerCommand,
    WebSocketCommand,
)
from app.services.session import end_session, start_question, submit_answer

COMMAND_MODELS: dict[str, type[WebSocketCommand]] = {
    "question.start": StartQuestionCommand,
    "answer.submit": SubmitAnswerCommand,
    "session.end": EndSessionCommand,
}


async def dispatch_session_command(
    session: AsyncSession,
    user: User,
    session_id: UUID,
    raw_command: dict[str, Any],
) -> WebSocketCommand:
    command_type = raw_command.get("type")
    if not isinstance(command_type, str) or command_type not in COMMAND_MODELS:
        raise ValueError("Unsupported command")

    command = COMMAND_MODELS[command_type].model_validate(raw_command)
    if isinstance(command, StartQuestionCommand):
        if user.role is not UserRole.ORGANIZER:
            raise PermissionError("Organizer role required")
        await start_question(
            session,
            user,
            session_id,
            command.question_id,
            duration_seconds=command.duration_seconds,
        )
    elif isinstance(command, SubmitAnswerCommand):
        if user.role is not UserRole.PARTICIPANT:
            raise PermissionError("Participant role required")
        await submit_answer(
            session,
            user,
            session_id,
            command.question_id,
            command.selected_answer_ids,
            command.text_answer,
        )
    else:
        if user.role is not UserRole.ORGANIZER:
            raise PermissionError("Organizer role required")
        await end_session(session, user, session_id)

    return command
