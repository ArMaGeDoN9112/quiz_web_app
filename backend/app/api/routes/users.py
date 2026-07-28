from fastapi import APIRouter

from app.api.dependencies.auth import CurrentUserDep
from app.db.session import SessionDep
from app.schemas.auth import ProfileUpdateRequest, UserResponse
from app.services.user import update_display_name

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def read_current_user(
    current_user: CurrentUserDep,
) -> UserResponse:
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    request: ProfileUpdateRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> UserResponse:
    return await update_display_name(session, current_user, request.display_name)
