import logging
from types import FrameType
from typing import cast

from loguru import logger


class InterceptHandler(logging.Handler):
    """Перенаправляет записи стандартного logging (uvicorn и др.) в loguru."""

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = cast(FrameType, frame.f_back)
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())
