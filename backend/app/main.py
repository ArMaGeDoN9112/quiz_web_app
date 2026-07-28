import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.quizzes import router as quizzes_router
from app.api.routes.sessions import router as sessions_router, websocket_router
from app.api.routes.users import router as users_router
from app.core.config import settings
from app.core.playback import automatic_playback_loop
from app.exceptions_handler import register_exception_handlers


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    stop_event = asyncio.Event()
    playback_task = asyncio.create_task(automatic_playback_loop(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        await playback_task


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    register_exception_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router)
    app.include_router(quizzes_router)
    app.include_router(sessions_router)
    app.include_router(websocket_router)
    app.include_router(users_router)
    app.include_router(health_router)
    return app


app = create_app()
