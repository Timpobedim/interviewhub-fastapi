from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class IHModel(BaseModel):
    """Базовая доменная модель: snake_case в Python, camelCase в JSON."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        from_attributes=True,
    )
