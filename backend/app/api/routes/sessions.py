from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, status

from app.api.dependencies.auth import CurrentUserDep, OrganizerUserDep, ParticipantUserDep
from app.core.live import broadcast_session_participants
from app.db.session import SessionDep
from app.schemas.session import (
    OrganizerSessionHistoryResponse,
    ParticipantSessionHistoryResponse,
    SessionJoinRequest,
    SessionLaunchRequest,
    SessionContextResponse,
    SessionParticipantResponse,
    SessionResponse,
    SessionResultResponse,
)
from app.services.session import (
    join_session,
    get_session_context,
    get_organizer_session_history,
    get_participant_session_history,
    get_session_result,
    launch_session,
)
from app.services.session_websocket import session_websocket_handler

router = APIRouter(prefix="/sessions", tags=["sessions"])
websocket_router = APIRouter(tags=["sessions"])


@router.get(
    "/history/participated",
    response_model=list[ParticipantSessionHistoryResponse],
)
async def participant_history_endpoint(
    current_user: ParticipantUserDep,
    session: SessionDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ParticipantSessionHistoryResponse]:
    return await get_participant_session_history(
        session,
        current_user,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/history/conducted",
    response_model=list[OrganizerSessionHistoryResponse],
)
async def organizer_history_endpoint(
    current_user: OrganizerUserDep,
    session: SessionDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[OrganizerSessionHistoryResponse]:
    return await get_organizer_session_history(
        session,
        current_user,
        limit=limit,
        offset=offset,
    )


@router.get("/{session_id}", response_model=SessionContextResponse)
async def session_context_endpoint(
    session_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> SessionContextResponse:
    return await get_session_context(session, current_user, session_id)


@router.get("/{session_id}/result", response_model=SessionResultResponse)
async def session_result_endpoint(
    session_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> SessionResultResponse:
    return await get_session_result(session, current_user, session_id)


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def launch_session_endpoint(
    request: SessionLaunchRequest,
    current_user: OrganizerUserDep,
    session: SessionDep,
) -> SessionResponse:
    return await launch_session(session, current_user, request.quiz_id)


@router.post(
    "/join",
    response_model=SessionParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def join_session_endpoint(
    request: SessionJoinRequest,
    current_user: ParticipantUserDep,
    session: SessionDep,
) -> SessionParticipantResponse:
    participant = await join_session(session, current_user, request.room_code)
    await broadcast_session_participants(participant.session_id)
    return participant


@websocket_router.websocket("/ws/sessions/{room_code}")
async def session_scoreboard_websocket(websocket: WebSocket, room_code: str) -> None:
    await session_websocket_handler(websocket, room_code)
