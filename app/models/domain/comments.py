from app.models.common import DateTimeModelMixin, IDModelMixin
from app.models.domain.ihmodel import IHModel
from app.models.domain.profiles import Profile


class Comment(IDModelMixin, DateTimeModelMixin, IHModel):
    body: str
    author: Profile
