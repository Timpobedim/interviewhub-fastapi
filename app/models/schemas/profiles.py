from app.models.domain.profiles import Profile
from app.models.schemas.ihschema import IHSchema


class ProfileInResponse(IHSchema):
    profile: Profile
