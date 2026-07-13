from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_user
from app.models import User
from app.db.session import get_db_session
from app.schemas.auth import ProfileUpdateRequest, UserResponse
from app.services.user import update_display_name
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def read_current_user(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    user = await update_display_name(session, current_user, request.display_name)
    return UserResponse.model_validate(user)
