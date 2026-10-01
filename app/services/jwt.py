from datetime import UTC, datetime, timedelta

import jwt
from pydantic import ValidationError

from app.models.domain.users import User
from app.models.schemas.jwt import JWTMeta, JWTUser

JWT_SUBJECT = "access"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # неделя


def create_jwt_token(
    *,
    jwt_content: dict[str, str],
    secret_key: str,
    expires_delta: timedelta,
) -> str:
    to_encode: dict[str, object] = dict(jwt_content)
    expire = datetime.now(UTC) + expires_delta
    to_encode.update(JWTMeta(exp=expire, sub=JWT_SUBJECT).model_dump())
    return jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)


def create_access_token_for_user(
    user: User,
    secret_key: str,
    expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
) -> str:
    return create_jwt_token(
        jwt_content=JWTUser(username=user.username).model_dump(),
        secret_key=secret_key,
        expires_delta=timedelta(minutes=expires_minutes),
    )


def get_username_from_token(token: str, secret_key: str) -> str:
    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as decode_error:
        raise ValueError("unable to decode JWT token") from decode_error

    if payload.get("sub") != JWT_SUBJECT:
        raise ValueError("unexpected token subject")

    try:
        return JWTUser.model_validate(payload).username
    except ValidationError as validation_error:
        raise ValueError("malformed payload in token") from validation_error
