from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_organizer
from app.db.session import get_db_session
from app.models import User
from app.schemas.quiz import (
    QuestionCreateRequest,
    QuestionResponse,
    QuizCreateRequest,
    QuizResponse,
    QuizUpdateRequest,
)
from app.services.quiz import (
    QuestionPositionConflictError,
    QuizNotFoundError,
    create_question,
    create_quiz,
    delete_quiz,
    get_quiz,
    list_questions,
    list_quizzes,
    update_quiz,
)

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


@router.post("", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def create_quiz_endpoint(
    request: QuizCreateRequest,
    current_user: User = Depends(require_organizer),
    session: AsyncSession = Depends(get_db_session),
) -> QuizResponse:
    quiz = await create_quiz(session, current_user, request)
    return QuizResponse.model_validate(quiz)


@router.get("", response_model=list[QuizResponse])
async def list_quizzes_endpoint(
    current_user: User = Depends(require_organizer),
    session: AsyncSession = Depends(get_db_session),
) -> list[QuizResponse]:
    quizzes = await list_quizzes(session, current_user)
    return [QuizResponse.model_validate(quiz) for quiz in quizzes]


@router.get("/{quiz_id}", response_model=QuizResponse)
async def get_quiz_endpoint(
    quiz_id: UUID,
    current_user: User = Depends(require_organizer),
    session: AsyncSession = Depends(get_db_session),
) -> QuizResponse:
    try:
        quiz = await get_quiz(session, current_user, quiz_id)
    except QuizNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        ) from error
    return QuizResponse.model_validate(quiz)


@router.patch("/{quiz_id}", response_model=QuizResponse)
async def update_quiz_endpoint(
    quiz_id: UUID,
    request: QuizUpdateRequest,
    current_user: User = Depends(require_organizer),
    session: AsyncSession = Depends(get_db_session),
) -> QuizResponse:
    try:
        quiz = await update_quiz(session, current_user, quiz_id, request)
    except QuizNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        ) from error
    return QuizResponse.model_validate(quiz)


@router.delete("/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quiz_endpoint(
    quiz_id: UUID,
    current_user: User = Depends(require_organizer),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    try:
        await delete_quiz(session, current_user, quiz_id)
    except QuizNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{quiz_id}/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_question_endpoint(
    quiz_id: UUID,
    request: QuestionCreateRequest,
    current_user: User = Depends(require_organizer),
    session: AsyncSession = Depends(get_db_session),
) -> QuestionResponse:
    try:
        question = await create_question(session, current_user, quiz_id, request)
    except QuizNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        ) from error
    except QuestionPositionConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Question position conflict; retry request",
        ) from error
    return QuestionResponse.model_validate(question)


@router.get("/{quiz_id}/questions", response_model=list[QuestionResponse])
async def list_questions_endpoint(
    quiz_id: UUID,
    current_user: User = Depends(require_organizer),
    session: AsyncSession = Depends(get_db_session),
) -> list[QuestionResponse]:
    try:
        questions = await list_questions(session, current_user, quiz_id)
    except QuizNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        ) from error
    return [QuestionResponse.model_validate(question) for question in questions]
