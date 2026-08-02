import logging
from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import QuizSession, SessionParticipant, User
from app.schemas.session import SessionLiveUpdateResponse, SessionParticipantResponse
from app.services.session import get_active_question, get_session_scoreboard

logger = logging.getLogger(__name__)


class ScoreboardHub:
    def __init__(self) -> None:
        self._connections: dict[UUID, dict[WebSocket, bool]] = defaultdict(dict)

    async def connect(self, session_id: UUID, websocket: WebSocket, is_organizer: bool) -> None:
        await websocket.accept()
        self._connections[session_id][websocket] = is_organizer

    def disconnect(self, session_id: UUID, websocket: WebSocket) -> None:
        connections = self._connections.get(session_id)
        if connections is None:
            return
        connections.pop(websocket, None)
        if not connections:
            self._connections.pop(session_id, None)

    async def broadcast(self, session_id: UUID, payload: dict[str, object]) -> None:
        for websocket in list(self._connections.get(session_id, ())):
            try:
                await websocket.send_json(payload)
            except RuntimeError:
                self.disconnect(session_id, websocket)

    async def broadcast_to_organizers(self, session_id: UUID, payload: dict[str, object]) -> None:
        for websocket, is_organizer in list(self._connections.get(session_id, {}).items()):
            if not is_organizer:
                continue
            try:
                await websocket.send_json(payload)
            except RuntimeError:
                self.disconnect(session_id, websocket)


scoreboard_hub = ScoreboardHub()


async def session_update_payload(session_id: UUID) -> dict[str, object] | None:
    async with AsyncSessionLocal() as session:
        quiz_session_result = await session.execute(
            select(QuizSession).where(QuizSession.id == session_id)
        )
        quiz_session = quiz_session_result.scalar_one_or_none()
        if quiz_session is None:
            return None

        organizer_result = await session.execute(
            select(User).where(User.id == quiz_session.organizer_id)
        )
        organizer = organizer_result.scalar_one_or_none()
        if organizer is None:
            return None

        scoreboard = await get_session_scoreboard(session, organizer, session_id)
        current_question = await get_active_question(session, quiz_session)
        return {
            "type": "session.updated",
            **SessionLiveUpdateResponse.model_validate(
                {
                    "scoreboard": scoreboard,
                    "current_question": current_question,
                }
            ).model_dump(mode="json"),
        }


async def broadcast_session_update(session_id: UUID) -> None:
    try:
        payload = await session_update_payload(session_id)
        if payload is not None:
            await scoreboard_hub.broadcast(session_id, payload)
    except Exception:
        logger.exception("Live session update failed for session %s", session_id)


async def broadcast_session_participants(session_id: UUID) -> None:
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SessionParticipant)
                .where(SessionParticipant.session_id == session_id)
                .order_by(SessionParticipant.joined_at)
            )
            participants = [
                SessionParticipantResponse.model_validate(participant).model_dump(mode="json")
                for participant in result.scalars().all()
            ]
        await scoreboard_hub.broadcast_to_organizers(
            session_id,
            {"type": "participants.updated", "participants": participants},
        )
    except Exception:
        logger.exception("Live participant update failed for session %s", session_id)
