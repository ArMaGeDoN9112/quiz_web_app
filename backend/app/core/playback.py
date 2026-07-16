import asyncio
import logging
from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import QuestionEvent, QuestionEventStatus, QuizSession, SessionStatus
from app.services.playback import advance_automatic_session
from app.services.session import utc_now

logger = logging.getLogger(__name__)


async def run_automatic_playback_once(
    now_factory: Callable[[], datetime] = utc_now,
) -> list[UUID]:
    now = now_factory()
    async with AsyncSessionLocal() as session:
        due_events_result = await session.execute(
            select(QuestionEvent.session_id)
            .join(QuizSession, QuestionEvent.session_id == QuizSession.id)
            .where(
                QuestionEvent.status == QuestionEventStatus.ACTIVE,
                QuestionEvent.ended_at.is_not(None),
                QuestionEvent.ended_at <= now,
                QuizSession.status == SessionStatus.ACTIVE,
            )
        )
        session_ids = set(due_events_result.scalars().all())

    advanced_session_ids: list[UUID] = []
    for session_id in session_ids:
        async with AsyncSessionLocal() as session:
            try:
                advanced = await advance_automatic_session(
                    session,
                    session_id,
                    now_factory=lambda: now,
                )
            except Exception:
                await session.rollback()
                logger.exception("Automatic playback failed for session %s", session_id)
                continue
            if advanced:
                advanced_session_ids.append(session_id)
    return advanced_session_ids


async def automatic_playback_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            await run_automatic_playback_once()
        except Exception:
            logger.exception("Automatic playback worker failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=1)
        except TimeoutError:
            continue
