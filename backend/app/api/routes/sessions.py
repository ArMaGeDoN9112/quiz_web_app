from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user, require_organizer, require_participant
from app.core.live import scoreboard_hub
from app.core.security import verify_access_token
from app.db.session import AsyncSessionLocal
from app.db.session import get_db_session
from app.models import QuizSession, SessionParticipant, User
from app.schemas.session import (
    QuestionAnswerResponse,
    QuestionEventResponse,
    CurrentQuestionResponse,
    OrganizerSessionHistoryResponse,
    ParticipantSessionHistoryResponse,
    SessionJoinRequest,
    SessionLaunchRequest,
    SessionContextResponse,
    SessionParticipantResponse,
    SessionResponse,
    SessionResultResponse,
    SessionScoreboardResponse,
    StartQuestionRequest,
    SubmitAnswerRequest,
)
from app.services.session import (
    join_session,
    end_session,
    get_session_scoreboard,
    get_current_question,
    get_session_context,
    get_organizer_session_history,
    get_participant_session_history,
    get_session_result,
    launch_session,
    start_question,
    submit_answer,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])
websocket_router = APIRouter(tags=["sessions"])


@router.get(
    "/history/participated",
    response_model=list[ParticipantSessionHistoryResponse],
)
async def participant_history_endpoint(
    current_user: User = Depends(require_participant),
    session: AsyncSession = Depends(get_db_session),
) -> list[ParticipantSessionHistoryResponse]:
    history = await get_participant_session_history(session, current_user)
    return [ParticipantSessionHistoryResponse.model_validate(item) for item in history]


@router.get(
    "/history/conducted",
    response_model=list[OrganizerSessionHistoryResponse],
)
async def organizer_history_endpoint(
    current_user: User = Depends(require_organizer),
    session: AsyncSession = Depends(get_db_session),
) -> list[OrganizerSessionHistoryResponse]:
    history = await get_organizer_session_history(session, current_user)
    return [OrganizerSessionHistoryResponse.model_validate(item) for item in history]


@router.get("/{session_id}", response_model=SessionContextResponse)
async def session_context_endpoint(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SessionContextResponse:
    context = await get_session_context(session, current_user, session_id)
    return SessionContextResponse(
        session=SessionResponse.model_validate(context.session),
        participant=(
            SessionParticipantResponse.model_validate(context.participant)
            if context.participant is not None
            else None
        ),
    )


@router.get("/{session_id}/result", response_model=SessionResultResponse)
async def session_result_endpoint(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SessionResultResponse:
    result = await get_session_result(session, current_user, session_id)
    return SessionResultResponse.model_validate(result)


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def launch_session_endpoint(
    request: SessionLaunchRequest,
    current_user: User = Depends(require_organizer),
    session: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    quiz_session = await launch_session(session, current_user, request.quiz_id)
    return SessionResponse.model_validate(quiz_session)


@router.post(
    "/join",
    response_model=SessionParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def join_session_endpoint(
    request: SessionJoinRequest,
    current_user: User = Depends(require_participant),
    session: AsyncSession = Depends(get_db_session),
) -> SessionParticipantResponse:
    participant = await join_session(session, current_user, request.room_code)
    return SessionParticipantResponse.model_validate(participant)


@router.post(
    "/{session_id}/questions/current",
    response_model=QuestionEventResponse,
)
async def start_question_endpoint(
    session_id: UUID,
    request: StartQuestionRequest,
    current_user: User = Depends(require_organizer),
    session: AsyncSession = Depends(get_db_session),
) -> QuestionEventResponse:
    question_event = await start_question(
        session, current_user, session_id, request.question_id,
        duration_seconds=request.duration_seconds,
    )
    return QuestionEventResponse.model_validate(question_event)


@router.get("/{session_id}/questions/current", response_model=CurrentQuestionResponse)
async def get_current_question_endpoint(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CurrentQuestionResponse:
    question = await get_current_question(session, current_user, session_id)
    return CurrentQuestionResponse.model_validate(question)


@router.post(
    "/{session_id}/answer",
    response_model=QuestionAnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_answer_endpoint(
    session_id: UUID,
    request: SubmitAnswerRequest,
    current_user: User = Depends(require_participant),
    session: AsyncSession = Depends(get_db_session),
) -> QuestionAnswerResponse:
    response = await submit_answer(
        session, current_user, session_id, request.question_id,
        request.selected_answer_ids, request.text_answer,
    )
    answer_response = QuestionAnswerResponse.model_validate(response)
    scoreboard = await get_session_scoreboard(session, current_user, session_id)
    scoreboard_response = _scoreboard_response(scoreboard)
    await scoreboard_hub.broadcast(
        session_id,
        {"type": "scoreboard.updated", "scoreboard": scoreboard_response.model_dump(mode="json")},
    )
    return answer_response


def _scoreboard_response(scoreboard: object) -> SessionScoreboardResponse:
    return SessionScoreboardResponse.model_validate(scoreboard, from_attributes=True)


@router.get("/{session_id}/scoreboard", response_model=SessionScoreboardResponse)
async def get_scoreboard_endpoint(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SessionScoreboardResponse:
    scoreboard = await get_session_scoreboard(session, current_user, session_id)
    return _scoreboard_response(scoreboard)


@router.post("/{session_id}/end", response_model=SessionScoreboardResponse)
async def end_session_endpoint(
    session_id: UUID,
    current_user: User = Depends(require_organizer),
    session: AsyncSession = Depends(get_db_session),
) -> SessionScoreboardResponse:
    scoreboard = await end_session(session, current_user, session_id)
    response = _scoreboard_response(scoreboard)
    await scoreboard_hub.broadcast(
        session_id,
        {"type": "scoreboard.updated", "scoreboard": response.model_dump(mode="json")},
    )
    return response


@websocket_router.websocket("/ws/sessions/{room_code}")
async def session_scoreboard_websocket(websocket: WebSocket, room_code: str) -> None:
    token = websocket.query_params.get("token")
    payload = verify_access_token(token) if token else None
    if payload is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user_id = UUID(payload["sub"])
    except (KeyError, TypeError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    async with AsyncSessionLocal() as session:
        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        quiz_session_result = await session.execute(
            select(QuizSession).where(QuizSession.room_code == room_code.strip().upper())
        )
        quiz_session = quiz_session_result.scalar_one_or_none()
        if user is None or quiz_session is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        if user.id != quiz_session.organizer_id:
            participant_result = await session.execute(
                select(SessionParticipant).where(
                    SessionParticipant.session_id == quiz_session.id,
                    SessionParticipant.user_id == user.id,
                )
            )
            if participant_result.scalar_one_or_none() is None:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

        scoreboard = await get_session_scoreboard(session, user, quiz_session.id)
        response = _scoreboard_response(scoreboard)

    await scoreboard_hub.connect(quiz_session.id, websocket)
    try:
        await websocket.send_json(
            {"type": "scoreboard.updated", "scoreboard": response.model_dump(mode="json")}
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        scoreboard_hub.disconnect(quiz_session.id, websocket)
