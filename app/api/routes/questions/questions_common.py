from fastapi import APIRouter, Depends, HTTPException, Query
from starlette import status

from app.api.dependencies.authentication import get_current_user_authorizer
from app.api.dependencies.database import get_repository
from app.api.dependencies.questions import get_question_by_slug_from_path
from app.db.repositories.questions import QuestionsRepository
from app.models.domain.questions import Question
from app.models.domain.users import User
from app.models.schemas.questions import (
    DEFAULT_QUESTIONS_LIMIT,
    DEFAULT_QUESTIONS_OFFSET,
    MAX_QUESTIONS_LIMIT,
    ListOfQuestionsInResponse,
    QuestionForResponse,
    QuestionInResponse,
)
from app.resources import strings

router = APIRouter()


@router.get(
    "/feed",
    response_model=ListOfQuestionsInResponse,
    name="questions:get-user-feed-questions",
)
async def get_questions_for_user_feed(
    limit: int = Query(DEFAULT_QUESTIONS_LIMIT, ge=1, le=MAX_QUESTIONS_LIMIT),
    offset: int = Query(DEFAULT_QUESTIONS_OFFSET, ge=0),
    user: User = Depends(get_current_user_authorizer()),
    questions_repo: QuestionsRepository = Depends(get_repository(QuestionsRepository)),
) -> ListOfQuestionsInResponse:
    questions, total = await questions_repo.get_questions_for_user_feed(
        user=user,
        limit=limit,
        offset=offset,
    )
    return ListOfQuestionsInResponse(
        questions=[QuestionForResponse.model_validate(question) for question in questions],
        questions_count=total,
    )


@router.post(
    "/{slug}/favorite",
    response_model=QuestionInResponse,
    name="questions:mark-question-favorite",
)
async def mark_question_as_favorite(
    question: Question = Depends(get_question_by_slug_from_path),
    user: User = Depends(get_current_user_authorizer()),
    questions_repo: QuestionsRepository = Depends(get_repository(QuestionsRepository)),
) -> QuestionInResponse:
    if question.favorited:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=strings.QUESTION_IS_ALREADY_FAVORITED,
        )

    await questions_repo.add_question_into_favorites(question=question, user=user)

    return QuestionInResponse(
        question=QuestionForResponse.model_validate(
            question.model_copy(
                update={"favorited": True, "favorites_count": question.favorites_count + 1},
            ),
        ),
    )


@router.delete(
    "/{slug}/favorite",
    response_model=QuestionInResponse,
    name="questions:unmark-question-favorite",
)
async def remove_question_from_favorites(
    question: Question = Depends(get_question_by_slug_from_path),
    user: User = Depends(get_current_user_authorizer()),
    questions_repo: QuestionsRepository = Depends(get_repository(QuestionsRepository)),
) -> QuestionInResponse:
    if not question.favorited:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=strings.QUESTION_IS_NOT_FAVORITED,
        )

    await questions_repo.remove_question_from_favorites(question=question, user=user)

    return QuestionInResponse(
        question=QuestionForResponse.model_validate(
            question.model_copy(
                update={"favorited": False, "favorites_count": question.favorites_count - 1},
            ),
        ),
    )
