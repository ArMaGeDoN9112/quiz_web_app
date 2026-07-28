from fastapi import APIRouter, status

from app.db.session import SessionDep
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
    session: SessionDep,
) -> UserResponse:
    return await register_user(session, request)


@router.post(
    "/login",
    response_model=TokenResponse
)
async def login(
    request: LoginRequest,
    session: SessionDep,
) -> TokenResponse:
    return await login_user(session, request)
