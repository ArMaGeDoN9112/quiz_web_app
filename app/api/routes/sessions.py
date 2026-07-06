from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_organizer
from app.db.session import get_db_session
from app.models import User
from app.schemas.session import SessionLaunchRequest, SessionResponse
from app.services.session import (
    RoomCodeConflictError,
    SessionQuizNotFoundError,
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
