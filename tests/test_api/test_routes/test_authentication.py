from datetime import timedelta

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette import status

from app.models.domain.users import User, UserInDB
from app.services import jwt


async def test_unable_to_login_without_token(app: FastAPI, client: AsyncClient) -> None:
    response = await client.get(app.url_path_for("users:get-current-user"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("header", ["Token abc.def.ghi", "Bearer", "Bearer a b", "abc"])
async def test_unable_to_login_with_wrong_token_prefix_or_format(
    app: FastAPI,
    client: AsyncClient,
    header: str,
) -> None:
    response = await client.get(
        app.url_path_for("users:get-current-user"),
        headers={"Authorization": header},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_unable_to_login_with_malformed_token(app: FastAPI, client: AsyncClient) -> None:
    response = await client.get(
        app.url_path_for("users:get-current-user"),
        headers={"Authorization": "Bearer definitely-not-a-jwt"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_unable_to_login_when_user_does_not_exist_anymore(
    app: FastAPI,
    client: AsyncClient,
    authorization_prefix: str,
) -> None:
    token = jwt.create_access_token_for_user(
        User(username="ghost", email="ghost@example.com"),
        "test-secret-key-for-pytest-only",
    )

    response = await client.get(
        app.url_path_for("users:get-current-user"),
        headers={"Authorization": f"{authorization_prefix} {token}"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_unable_to_login_with_expired_token(
    app: FastAPI,
    client: AsyncClient,
    test_user: UserInDB,
    authorization_prefix: str,
) -> None:
    token = jwt.create_jwt_token(
        jwt_content={"username": test_user.username},
        secret_key="test-secret-key-for-pytest-only",
        expires_delta=timedelta(minutes=-1),
    )

    response = await client.get(
        app.url_path_for("users:get-current-user"),
        headers={"Authorization": f"{authorization_prefix} {token}"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_optional_auth_route_accepts_anonymous_and_rejects_bad_token(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    anonymous = await client.get(app.url_path_for("questions:list-questions"))
    bad_token = await client.get(
        app.url_path_for("questions:list-questions"),
        headers={"Authorization": "Bearer broken"},
    )

    assert anonymous.status_code == status.HTTP_200_OK
    assert bad_token.status_code == status.HTTP_401_UNAUTHORIZED
