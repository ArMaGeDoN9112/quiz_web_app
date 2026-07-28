from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.dependencies.auth import OrganizerUserDep
from app.db.session import SessionDep
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
    current_user: OrganizerUserDep,
    session: SessionDep,
) -> QuizResponse:
    return await create_quiz(session, current_user, request)


@router.get("", response_model=list[QuizResponse])
async def list_quizzes_endpoint(
    current_user: OrganizerUserDep,
    session: SessionDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[QuizResponse]:
    return await list_quizzes(session, current_user, limit=limit, offset=offset)


@router.get("/{quiz_id}", response_model=QuizResponse)
async def get_quiz_endpoint(
    quiz_id: UUID,
    current_user: OrganizerUserDep,
    session: SessionDep,
) -> QuizResponse:
    return await get_quiz(session, current_user, quiz_id)


@router.patch("/{quiz_id}", response_model=QuizResponse)
async def update_quiz_endpoint(
    quiz_id: UUID,
    request: QuizUpdateRequest,
    current_user: OrganizerUserDep,
    session: SessionDep,
) -> QuizResponse:
    return await update_quiz(session, current_user, quiz_id, request)


@router.delete("/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quiz_endpoint(
    quiz_id: UUID,
    current_user: OrganizerUserDep,
    session: SessionDep,
) -> None:
    await delete_quiz(session, current_user, quiz_id)


@router.post(
    "/{quiz_id}/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_question_endpoint(
    quiz_id: UUID,
    request: QuestionCreateRequest,
    current_user: OrganizerUserDep,
    session: SessionDep,
) -> QuestionResponse:
    return await create_question(session, current_user, quiz_id, request)


@router.put(
    "/{quiz_id}/questions/{question_id}",
    response_model=QuestionResponse,
)
async def update_question_endpoint(
    quiz_id: UUID,
    question_id: UUID,
    request: QuestionCreateRequest,
    current_user: OrganizerUserDep,
    session: SessionDep,
) -> QuestionResponse:
    return await update_question(session, current_user, quiz_id, question_id, request)


@router.get("/{quiz_id}/questions", response_model=list[QuestionResponse])
async def list_questions_endpoint(
    quiz_id: UUID,
    current_user: OrganizerUserDep,
    session: SessionDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[QuestionResponse]:
    return await list_questions(
        session,
        current_user,
        quiz_id,
        limit=limit,
        offset=offset,
    )
