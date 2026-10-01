import asyncpg
from fastapi import FastAPI
from loguru import logger

from app.core.settings.app import AppSettings


async def connect_to_db(app: FastAPI, settings: AppSettings) -> None:
    logger.info("Подключение к PostgreSQL")

    app.state.pool = await asyncpg.create_pool(
        settings.database_dsn,
        min_size=settings.min_connection_count,
        max_size=settings.max_connection_count,
    )

    logger.info("Пул соединений создан")


async def close_db_connection(app: FastAPI) -> None:
    logger.info("Закрытие пула соединений")

    await app.state.pool.close()

    logger.info("Пул соединений закрыт")
