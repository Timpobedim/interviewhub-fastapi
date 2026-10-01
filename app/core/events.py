from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI

from app.core.settings.app import AppSettings
from app.db.events import close_db_connection, connect_to_db


def create_lifespan(
    settings: AppSettings,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Жизненный цикл приложения: пул соединений открывается на старте и закрывается на остановке.

    Обработчики startup/shutdown в современных FastAPI/Starlette объявлены устаревшими,
    поэтому используется lifespan.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await connect_to_db(app, settings)
        try:
            yield
        finally:
            await close_db_connection(app)

    return lifespan
