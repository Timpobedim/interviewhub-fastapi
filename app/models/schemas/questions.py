from pydantic import BaseModel, Field, field_validator

from app.models.domain.questions import Grade, Question
from app.models.schemas.ihschema import IHSchema

DEFAULT_QUESTIONS_LIMIT = 20
DEFAULT_QUESTIONS_OFFSET = 0
MAX_QUESTIONS_LIMIT = 100
MAX_TAGS_PER_QUESTION = 10
MAX_TAG_LENGTH = 40


def normalize_tags(tags: list[str]) -> list[str]:
    """Приводит теги к нижнему регистру, убирает пустые и дубли, сохраняя порядок."""
    seen: dict[str, None] = {}
    for raw_tag in tags:
        tag = raw_tag.strip().lower()
        if tag:
            seen.setdefault(tag[:MAX_TAG_LENGTH], None)
    return list(seen)


class QuestionForResponse(IHSchema, Question):
    tags: list[str] = Field(..., alias="tagList")


class QuestionInResponse(IHSchema):
    question: QuestionForResponse


class QuestionInCreate(IHSchema):
    title: str = Field(min_length=5, max_length=300)
    summary: str = Field(min_length=1, max_length=1000)
    answer: str = Field(min_length=1)
    grade: Grade = Grade.junior
    company: str | None = Field(None, max_length=120)
    tags: list[str] = Field(
        default_factory=list,
        alias="tagList",
        max_length=MAX_TAGS_PER_QUESTION,
    )

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, tags: list[str]) -> list[str]:
        return normalize_tags(tags)


class QuestionInUpdate(IHSchema):
    title: str | None = Field(None, min_length=5, max_length=300)
    summary: str | None = Field(None, min_length=1, max_length=1000)
    answer: str | None = Field(None, min_length=1)
    grade: Grade | None = None
    company: str | None = Field(None, max_length=120)
    tags: list[str] | None = Field(None, alias="tagList", max_length=MAX_TAGS_PER_QUESTION)

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, tags: list[str] | None) -> list[str] | None:
        return normalize_tags(tags) if tags is not None else None


class ListOfQuestionsInResponse(IHSchema):
    questions: list[QuestionForResponse]
    questions_count: int


class QuestionsFilters(BaseModel):
    tag: str | None = None
    author: str | None = None
    favorited: str | None = None
    grade: Grade | None = None
    company: str | None = None
    limit: int = Field(DEFAULT_QUESTIONS_LIMIT, ge=1, le=MAX_QUESTIONS_LIMIT)
    offset: int = Field(DEFAULT_QUESTIONS_OFFSET, ge=0)
