from collections.abc import AsyncIterator, Callable
from typing import Any, cast

from asyncpg import Connection
from asyncpg.pool import Pool
from fastapi import Depends
from starlette.requests import Request

from app.db.repositories.base import BaseRepository


def _get_db_pool(request: Request) -> Pool:
    pool: Pool = request.app.state.pool
    return pool


def get_repository[RepositoryT: BaseRepository](
    repo_type: type[RepositoryT],
) -> Callable[..., Any]:
    """Фабрика зависимостей: выдаёт репозиторий с соединением из пула на время запроса."""

    async def _get_repo(pool: Pool = Depends(_get_db_pool)) -> AsyncIterator[RepositoryT]:
        async with pool.acquire() as conn:
            # PoolConnectionProxy проксирует все методы Connection
            yield repo_type(cast(Connection, conn))

    return _get_repo
