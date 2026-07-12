from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

DUMMY_PASSWORD_HASH = hash_password("dummy password for missing login users")


class DuplicateEmailError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


async def register_user(session: AsyncSession, data: RegisterRequest) -> User:
    existing_user = await session.execute(select(User).where(User.email == data.email))
    if existing_user.scalar_one_or_none() is not None:
        raise DuplicateEmailError

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    session.add(user)

    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise DuplicateEmailError from error

    await session.refresh(user)
    return user


async def login_user(session: AsyncSession, data: LoginRequest) -> TokenResponse:
    user_result = await session.execute(select(User).where(User.email == data.email))
    user = user_result.scalar_one_or_none()
    password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    if not verify_password(data.password, password_hash):
        raise InvalidCredentialsError
    if user is None:
        raise InvalidCredentialsError

    token = create_access_token(subject=str(user.id), role=user.role.value)
    return TokenResponse(access_token=token)
