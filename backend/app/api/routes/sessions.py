from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
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
    SessionParticipantResponse,
    SessionResponse,
    SessionResultResponse,
    SessionScoreboardResponse,
    StartQuestionRequest,
    SubmitAnswerRequest,
)
from app.services.session import (
    ActiveQuestionConflictError,
    AnswerOutsideQuestionWindowError,
    AnswerParticipantNotFoundError,
    AnswerQuestionNotFoundError,
    AnswerSessionEndedError,
    DuplicateQuestionEventError,
    DuplicateQuestionResponseError,
    DuplicateSessionParticipantError,
    CurrentQuestionAccessError,
    CurrentQuestionNotFoundError,
    EndSessionNotFoundError,
    SessionResultAccessError,
    SessionResultNotFoundError,
    InvalidQuestionAnswerSelectionError,
    QuestionNotInSessionQuizError,
    ProfileDisplayNameRequiredError,
    RoomCodeConflictError,
    SessionScoreboardAccessError,
    SessionScoreboardNotFoundError,
    SessionQuestionNotFoundError,
    SessionNotJoinableError,
    SessionQuizNotFoundError,
    StartQuestionSessionEndedError,
    StartQuestionSessionNotFoundError,
    join_session,
    end_session,
    get_session_scoreboard,
    get_current_question,
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


@router.get("/{session_id}/result", response_model=SessionResultResponse)
async def session_result_endpoint(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SessionResultResponse:
    try:
        result = await get_session_result(session, current_user, session_id)
    except SessionResultNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session result not found") from error
    except SessionResultAccessError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session result access denied",
        ) from error
    return SessionResultResponse.model_validate(result)


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def launch_session_endpoint(
    request: SessionLaunchRequest,
    current_user: User = Depends(require_organizer),
    session: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    try:
        quiz_session = await launch_session(session, current_user, request.quiz_id)
    except SessionQuizNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        ) from error
    except RoomCodeConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Room code conflict; retry request",
        ) from error

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
    try:
        participant = await join_session(
            session,
            current_user,
            request.room_code,
        )
    except SessionNotJoinableError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session is not joinable",
        ) from error
    except DuplicateSessionParticipantError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already joined session",
        ) from error
    except ProfileDisplayNameRequiredError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile display name required",
        ) from error

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
    try:
        question_event = await start_question(
            session,
            current_user,
            session_id,
            request.question_id,
            duration_seconds=request.duration_seconds,
        )
    except StartQuestionSessionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        ) from error
    except StartQuestionSessionEndedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session is ended",
        ) from error
    except SessionQuestionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        ) from error
    except QuestionNotInSessionQuizError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Question does not belong to session quiz",
        ) from error
    except DuplicateQuestionEventError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Question already used in session",
        ) from error
    except ActiveQuestionConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active question conflict; retry request",
        ) from error

    return QuestionEventResponse.model_validate(question_event)


@router.get("/{session_id}/questions/current", response_model=CurrentQuestionResponse)
async def get_current_question_endpoint(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CurrentQuestionResponse:
    try:
        question = await get_current_question(session, current_user, session_id)
    except CurrentQuestionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active question",
        ) from error
    except CurrentQuestionAccessError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session access denied",
        ) from error
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
    try:
        response = await submit_answer(
            session,
            current_user,
            session_id,
            request.question_id,
            request.selected_answer_ids,
            request.text_answer,
        )
    except AnswerParticipantNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant session not found",
        ) from error
    except AnswerSessionEndedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session is ended",
        ) from error
    except AnswerQuestionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active question not found",
        ) from error
    except AnswerOutsideQuestionWindowError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Question is not accepting answers",
        ) from error
    except InvalidQuestionAnswerSelectionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid answer selection",
        ) from error
    except DuplicateQuestionResponseError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Question already answered",
        ) from error

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
    try:
        scoreboard = await get_session_scoreboard(session, current_user, session_id)
    except SessionScoreboardNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found") from error
    except SessionScoreboardAccessError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session access denied") from error
    return _scoreboard_response(scoreboard)


@router.post("/{session_id}/end", response_model=SessionScoreboardResponse)
async def end_session_endpoint(
    session_id: UUID,
    current_user: User = Depends(require_organizer),
    session: AsyncSession = Depends(get_db_session),
) -> SessionScoreboardResponse:
    try:
        scoreboard = await end_session(session, current_user, session_id)
    except EndSessionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found") from error
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
