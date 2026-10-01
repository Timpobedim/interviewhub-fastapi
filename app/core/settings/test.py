import logging

from pydantic import PostgresDsn, SecretStr

from app.core.settings.app import AppSettings


class TestAppSettings(AppSettings):
    debug: bool = True

    title: str = "Test InterviewHub API"

    secret_key: SecretStr = SecretStr("test-secret-key")

    database_url: PostgresDsn = PostgresDsn(
        "postgresql://postgres:postgres@localhost:5432/interviewhub_test",
    )
    max_connection_count: int = 5
    min_connection_count: int = 1

    logging_level: int = logging.DEBUG
