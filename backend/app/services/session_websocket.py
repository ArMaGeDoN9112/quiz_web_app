import logging
from typing import Any
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.core.live import broadcast_session_update, scoreboard_hub, session_update_payload
from app.core.security import verify_access_token
from app.db.session import AsyncSessionLocal
from app.models import QuizSession, SessionParticipant, User
from app.services.session_commands import dispatch_session_command

logger = logging.getLogger(__name__)


async def session_websocket_handler(websocket: WebSocket, room_code: str) -> None:
    connection = await _authorize(websocket, room_code)
    if connection is None:
        return

    user, session_id = connection
    await scoreboard_hub.connect(session_id, websocket)
    try:
        initial_payload = await session_update_payload(session_id)
        if initial_payload is None:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return
        await websocket.send_json(initial_payload)
        await _receive_commands(websocket, user, session_id)
    except WebSocketDisconnect:
        pass
    finally:
        scoreboard_hub.disconnect(session_id, websocket)


async def _authorize(websocket: WebSocket, room_code: str) -> tuple[User, UUID] | None:
    token = websocket.query_params.get("token")
    payload = verify_access_token(token) if token else None
    if payload is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    try:
        user_id = UUID(payload["sub"])
    except (KeyError, TypeError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    async with AsyncSessionLocal() as session:
        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        quiz_session_result = await session.execute(
            select(QuizSession).where(QuizSession.room_code == room_code.strip().upper())
        )
        quiz_session = quiz_session_result.scalar_one_or_none()
        if user is None or quiz_session is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        if user.id != quiz_session.organizer_id:
            participant_result = await session.execute(
                select(SessionParticipant).where(
                    SessionParticipant.session_id == quiz_session.id,
                    SessionParticipant.user_id == user.id,
                )
            )
            if participant_result.scalar_one_or_none() is None:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return None

        return user, quiz_session.id


async def _receive_commands(websocket: WebSocket, user: User, session_id: UUID) -> None:
    while True:
        message = await websocket.receive_json()
        request_id = message.get("request_id") if isinstance(message, dict) else None
        try:
            if not isinstance(message, dict) or not isinstance(message.get("type"), str):
                raise ValueError("Invalid command")
            async with AsyncSessionLocal() as command_session:
                command = await dispatch_session_command(command_session, user, session_id, message)
            await websocket.send_json(
                {"type": "command.accepted", "request_id": str(command.request_id)}
            )
            await broadcast_session_update(session_id)
        except (ValueError, PermissionError) as error:
            await websocket.send_json(
                {"type": "command.error", "request_id": str(request_id or ""), "detail": str(error)}
            )
        except Exception:
            logger.exception(
                "WebSocket command failed: %s",
                message.get("type") if isinstance(message, dict) else "invalid",
            )
            await websocket.send_json(
                {
                    "type": "command.error",
                    "request_id": str(request_id or ""),
                    "detail": "Command could not be completed",
                }
            )
