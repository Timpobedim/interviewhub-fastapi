from collections.abc import Sequence

from app.db.queries.queries import queries
from app.db.repositories.base import BaseRepository


class TagsRepository(BaseRepository):
    async def get_all_tags(self) -> list[str]:
        # aiosql ≥ 10: SELECT без суффикса возвращает асинхронный генератор строк
        return [row["tag"] async for row in queries.get_all_tags(self.connection)]

    async def create_tags_that_dont_exist(self, *, tags: Sequence[str]) -> None:
        await queries.create_new_tags(self.connection, [{"tag": tag} for tag in tags])
