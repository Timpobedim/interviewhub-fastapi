from pydantic import Field

from app.models.domain.comments import Comment
from app.models.schemas.ihschema import IHSchema


class ListOfCommentsInResponse(IHSchema):
    comments: list[Comment]


class CommentInResponse(IHSchema):
    comment: Comment


class CommentInCreate(IHSchema):
    body: str = Field(min_length=1, max_length=5000)
