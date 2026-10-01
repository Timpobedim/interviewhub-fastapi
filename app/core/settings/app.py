import logging
import sys
from typing import Any

from loguru import logger
from pydantic import Field, PostgresDsn, SecretStr
from pydantic_settings import SettingsConfigDict

from app.core.logging import InterceptHandler
from app.core.settings.base import BaseAppSettings


class AppSettings(BaseAppSettings):
    debug: bool = False
    docs_url: str = "/docs"
    openapi_url: str = "/openapi.json"
    redoc_url: str = "/redoc"
    title: str = "InterviewHub API"
    version: str = "1.0.0"

    database_url: PostgresDsn
    max_connection_count: int = 10
    min_connection_count: int = 2

    secret_key: SecretStr

    api_prefix: str = "/api"

    jwt_token_prefix: str = "Bearer"  # noqa: S105 — это схема авторизации, а не секрет
    access_token_expire_minutes: int = 60 * 24 * 7

    allowed_hosts: list[str] = Field(default_factory=lambda: ["*"])

    logging_level: int = logging.INFO
    loggers: tuple[str, ...] = ("uvicorn.asgi", "uvicorn.access")

    model_config = SettingsConfigDict(validate_assignment=True)

    @property
    def fastapi_kwargs(self) -> dict[str, Any]:
        return {
            "debug": self.debug,
            "docs_url": self.docs_url,
            "openapi_url": self.openapi_url,
            "redoc_url": self.redoc_url,
            "title": self.title,
            "version": self.version,
        }

    @property
    def database_dsn(self) -> str:
        return str(self.database_url)

    def configure_logging(self) -> None:
        logging.getLogger().handlers = [InterceptHandler()]
        for logger_name in self.loggers:
            logging_logger = logging.getLogger(logger_name)
            logging_logger.handlers = [InterceptHandler(level=self.logging_level)]

        logger.configure(handlers=[{"sink": sys.stderr, "level": self.logging_level}])
