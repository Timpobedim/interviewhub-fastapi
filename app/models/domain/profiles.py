from app.models.domain.ihmodel import IHModel


class Profile(IHModel):
    username: str
    bio: str = ""
    image: str | None = None
    following: bool = False
