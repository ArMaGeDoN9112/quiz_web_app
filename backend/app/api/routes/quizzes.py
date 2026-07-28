from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
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
    create_question,
    create_quiz,
    delete_quiz,
    get_quiz,
    list_questions,
    list_quizzes,
    update_quiz,
    update_question,
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
    quiz = await get_quiz(session, current_user, quiz_id)
    return QuizResponse.model_validate(quiz)


@router.patch("/{quiz_id}", response_model=QuizResponse)
async def update_quiz_endpoint(
    quiz_id: UUID,
    request: QuizUpdateRequest,
    current_user: User = Depends(require_organizer),
    session: AsyncSession = Depends(get_db_session),
) -> QuizResponse:
    quiz = await update_quiz(session, current_user, quiz_id, request)
    return QuizResponse.model_validate(quiz)


@router.delete("/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quiz_endpoint(
    quiz_id: UUID,
    current_user: User = Depends(require_organizer),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    await delete_quiz(session, current_user, quiz_id)
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
    question = await create_question(session, current_user, quiz_id, request)
    return QuestionResponse.model_validate(question)


@router.put(
    "/{quiz_id}/questions/{question_id}",
    response_model=QuestionResponse,
)
async def update_question_endpoint(
    quiz_id: UUID,
    question_id: UUID,
    request: QuestionCreateRequest,
    current_user: User = Depends(require_organizer),
    session: AsyncSession = Depends(get_db_session),
) -> QuestionResponse:
    question = await update_question(session, current_user, quiz_id, question_id, request)
    return QuestionResponse.model_validate(question)


@router.get("/{quiz_id}/questions", response_model=list[QuestionResponse])
async def list_questions_endpoint(
    quiz_id: UUID,
    current_user: User = Depends(require_organizer),
    session: AsyncSession = Depends(get_db_session),
) -> list[QuestionResponse]:
    questions = await list_questions(session, current_user, quiz_id)
    return [QuestionResponse.model_validate(question) for question in questions]
