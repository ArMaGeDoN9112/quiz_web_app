from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_organizer, require_participant
from app.db.session import get_db_session
from app.models import User
from app.schemas.session import (
    SessionJoinRequest,
    SessionLaunchRequest,
    SessionParticipantResponse,
    SessionResponse,
)
from app.services.session import (
    DuplicateSessionParticipantError,
    RoomCodeConflictError,
    SessionNotJoinableError,
    SessionQuizNotFoundError,
    join_session,
    launch_session,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def launch_session_endpoint(
    request: SessionLaunchRequest,
    current_user: User = Depends(require_organizer),
    session: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    try:
        quiz_session = await launch_session(session, current_user, request.quiz_id)
    except SessionQuizNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        ) from error
    except RoomCodeConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Room code conflict; retry request",
        ) from error

    return SessionResponse.model_validate(quiz_session)


@router.post(
    "/join",
    response_model=SessionParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def join_session_endpoint(
    request: SessionJoinRequest,
    current_user: User = Depends(require_participant),
    session: AsyncSession = Depends(get_db_session),
) -> SessionParticipantResponse:
    try:
        participant = await join_session(
            session,
            current_user,
            request.room_code,
            request.display_name,
        )
    except SessionNotJoinableError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session is not joinable",
        ) from error
    except DuplicateSessionParticipantError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already joined session",
        ) from error

    return SessionParticipantResponse.model_validate(participant)
