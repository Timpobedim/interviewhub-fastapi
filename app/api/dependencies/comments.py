from fastapi import Depends, HTTPException, Path
from starlette import status

from app.api.dependencies.authentication import get_current_user_authorizer
from app.api.dependencies.database import get_repository
from app.api.dependencies.questions import get_question_by_slug_from_path
from app.db.errors import EntityDoesNotExistError
from app.db.repositories.comments import CommentsRepository
from app.models.domain.comments import Comment
from app.models.domain.questions import Question
from app.models.domain.users import User
from app.resources import strings
from app.services.comments import check_user_can_modify_comment


async def get_comment_by_id_from_path(
    comment_id: int = Path(..., ge=1),
    question: Question = Depends(get_question_by_slug_from_path),
    user: User | None = Depends(get_current_user_authorizer(required=False)),
    comments_repo: CommentsRepository = Depends(get_repository(CommentsRepository)),
) -> Comment:
    try:
        return await comments_repo.get_comment_by_id(
            comment_id=comment_id,
            question=question,
            user=user,
        )
    except EntityDoesNotExistError as existence_error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=strings.COMMENT_DOES_NOT_EXIST,
        ) from existence_error


def check_comment_modification_permissions(
    comment: Comment = Depends(get_comment_by_id_from_path),
    user: User = Depends(get_current_user_authorizer()),
) -> None:
    if not check_user_can_modify_comment(comment, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=strings.USER_IS_NOT_AUTHOR_OF_COMMENT,
        )
