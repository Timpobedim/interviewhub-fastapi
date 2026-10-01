from pydantic import EmailStr, Field, HttpUrl

from app.models.domain.users import User
from app.models.schemas.ihschema import IHSchema

USERNAME_PATTERN = r"^[A-Za-z0-9_.-]+$"


class UserInLogin(IHSchema):
    email: EmailStr
    password: str


class UserInCreate(IHSchema):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    username: str = Field(min_length=3, max_length=40, pattern=USERNAME_PATTERN)


class UserInUpdate(IHSchema):
    username: str | None = Field(None, min_length=3, max_length=40, pattern=USERNAME_PATTERN)
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8, max_length=128)
    bio: str | None = Field(None, max_length=1000)
    image: HttpUrl | None = None


class UserWithToken(User):
    token: str


class UserInResponse(IHSchema):
    user: UserWithToken
