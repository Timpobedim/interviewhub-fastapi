from fastapi import Depends, HTTPException, Path, Query
from starlette import status

from app.api.dependencies.authentication import get_current_user_authorizer
from app.api.dependencies.database import get_repository
from app.db.errors import EntityDoesNotExistError
from app.db.repositories.questions import QuestionsRepository
from app.models.domain.questions import Grade, Question
from app.models.domain.users import User
from app.models.schemas.questions import (
    DEFAULT_QUESTIONS_LIMIT,
    DEFAULT_QUESTIONS_OFFSET,
    MAX_QUESTIONS_LIMIT,
    QuestionsFilters,
)
from app.resources import strings
from app.services.questions import check_user_can_modify_question


def get_questions_filters(
    tag: str | None = None,
    author: str | None = None,
    favorited: str | None = None,
    grade: Grade | None = None,
    company: str | None = Query(None, max_length=120),
    limit: int = Query(DEFAULT_QUESTIONS_LIMIT, ge=1, le=MAX_QUESTIONS_LIMIT),
    offset: int = Query(DEFAULT_QUESTIONS_OFFSET, ge=0),
) -> QuestionsFilters:
    return QuestionsFilters(
        tag=tag,
        author=author,
        favorited=favorited,
        grade=grade,
        company=company,
        limit=limit,
        offset=offset,
    )


async def get_question_by_slug_from_path(
    slug: str = Path(..., min_length=1),
    user: User | None = Depends(get_current_user_authorizer(required=False)),
    questions_repo: QuestionsRepository = Depends(get_repository(QuestionsRepository)),
) -> Question:
    try:
        return await questions_repo.get_question_by_slug(slug=slug, requested_user=user)
    except EntityDoesNotExistError as existence_error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=strings.QUESTION_DOES_NOT_EXIST_ERROR,
        ) from existence_error


def check_question_modification_permissions(
    current_question: Question = Depends(get_question_by_slug_from_path),
    user: User = Depends(get_current_user_authorizer()),
) -> None:
    if not check_user_can_modify_question(current_question, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=strings.USER_IS_NOT_AUTHOR_OF_QUESTION,
        )
