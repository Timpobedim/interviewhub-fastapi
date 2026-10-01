from pydantic import BaseModel


class TagsInList(BaseModel):
    tags: list[str]
