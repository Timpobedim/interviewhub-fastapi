import logging

from app.core.settings.app import AppSettings


class DevAppSettings(AppSettings):
    debug: bool = True

    title: str = "Dev InterviewHub API"

    logging_level: int = logging.DEBUG
