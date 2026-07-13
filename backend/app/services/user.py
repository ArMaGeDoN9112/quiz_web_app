from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def update_display_name(
    session: AsyncSession,
    user: User,
    display_name: str,
) -> User:
    user.display_name = display_name
    await session.commit()
    await session.refresh(user)
    return user
