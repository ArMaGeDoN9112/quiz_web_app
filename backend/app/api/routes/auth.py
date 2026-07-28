from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth import login_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    user = await register_user(session, request)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse
)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    return await login_user(session, request)
