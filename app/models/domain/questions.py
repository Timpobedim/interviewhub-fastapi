from enum import StrEnum

from app.models.common import DateTimeModelMixin, IDModelMixin
from app.models.domain.ihmodel import IHModel
from app.models.domain.profiles import Profile


class Grade(StrEnum):
    """Уровень, на котором обычно задают вопрос."""

    junior = "junior"
    middle = "middle"
    senior = "senior"


class Question(IDModelMixin, DateTimeModelMixin, IHModel):
    slug: str
    title: str
    summary: str
    answer: str
    grade: Grade
    company: str | None = None
    tags: list[str]
    author: Profile
    favorited: bool
    favorites_count: int
