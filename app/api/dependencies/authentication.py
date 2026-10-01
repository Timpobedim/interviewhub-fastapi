from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette import status

from app.api.dependencies.database import get_repository
from app.core.config import get_app_settings
from app.core.settings.app import AppSettings
from app.db.errors import EntityDoesNotExistError
from app.db.repositories.users import UsersRepository
from app.models.domain.users import User
from app.resources import strings
from app.services import jwt

HEADER_KEY = "Authorization"

# auto_error=False: отсутствие заголовка обрабатываем сами, чтобы вернуть 401 с понятным текстом.
_authorization_header = APIKeyHeader(
    name=HEADER_KEY,
    auto_error=False,
    description="Токен в формате: Bearer <JWT>",
)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user_authorizer(*, required: bool = True) -> Callable[..., Any]:
    return _get_current_user if required else _get_current_user_optional


def _extract_token(header_value: str, settings: AppSettings) -> str:
    try:
        token_prefix, token = header_value.split(" ")
    except ValueError as split_error:
        raise _unauthorized(strings.WRONG_TOKEN_PREFIX) from split_error

    if token_prefix != settings.jwt_token_prefix:
        raise _unauthorized(strings.WRONG_TOKEN_PREFIX)

    return token


def _get_authorization_header(
    header_value: str | None = Security(_authorization_header),
    settings: AppSettings = Depends(get_app_settings),
) -> str:
    if not header_value:
        raise _unauthorized(strings.AUTHENTICATION_REQUIRED)

    return _extract_token(header_value, settings)


def _get_authorization_header_optional(
    header_value: str | None = Security(_authorization_header),
    settings: AppSettings = Depends(get_app_settings),
) -> str:
    if header_value:
        return _extract_token(header_value, settings)

    return ""


async def _get_current_user(
    users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
    token: str = Depends(_get_authorization_header),
    settings: AppSettings = Depends(get_app_settings),
) -> User:
    try:
        username = jwt.get_username_from_token(token, settings.secret_key.get_secret_value())
    except ValueError as token_error:
        raise _unauthorized(strings.MALFORMED_PAYLOAD) from token_error

    try:
        return await users_repo.get_user_by_username(username=username)
    except EntityDoesNotExistError as existence_error:
        raise _unauthorized(strings.MALFORMED_PAYLOAD) from existence_error


async def _get_current_user_optional(
    users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
    token: str = Depends(_get_authorization_header_optional),
    settings: AppSettings = Depends(get_app_settings),
) -> User | None:
    if token:
        return await _get_current_user(users_repo, token, settings)

    return None
