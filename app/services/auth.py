from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import User
from app.schemas.auth import RegisterRequest


class DuplicateEmailError(Exception):
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
