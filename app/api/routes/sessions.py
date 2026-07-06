from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_organizer, require_participant
from app.db.session import get_db_session
from app.models import User
from app.schemas.session import (
    QuestionAnswerResponse,
    QuestionEventResponse,
    SessionJoinRequest,
    SessionLaunchRequest,
    SessionParticipantResponse,
    SessionResponse,
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
    InvalidQuestionAnswerSelectionError,
    QuestionNotInSessionQuizError,
    RoomCodeConflictError,
    SessionQuestionNotFoundError,
    SessionNotJoinableError,
    SessionQuizNotFoundError,
    StartQuestionSessionEndedError,
    StartQuestionSessionNotFoundError,
    join_session,
    launch_session,
    start_question,
    submit_answer,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


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
            request.display_name,
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

    return QuestionAnswerResponse.model_validate(response)
