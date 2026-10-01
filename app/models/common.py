from datetime import datetime

from pydantic import BaseModel, Field


class DateTimeModelMixin(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None


class IDModelMixin(BaseModel):
    id_: int = Field(0, alias="id")
