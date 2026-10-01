from collections.abc import Awaitable, Callable

import pytest
from asyncpg.pool import Pool
from fastapi import FastAPI
from httpx import AsyncClient
from starlette import status

from app.db.repositories.users import UsersRepository
from app.models.domain.users import UserInDB
from app.models.schemas.users import UserInResponse


async def test_user_success_registration(app: FastAPI, client: AsyncClient, pool: Pool) -> None:
    email, username, password = "Candidate@Example.com", "candidate", "strong-password"
    registration_json = {"user": {"email": email, "username": username, "password": password}}

    response = await client.post(app.url_path_for("auth:register"), json=registration_json)

    assert response.status_code == status.HTTP_201_CREATED
    user = UserInResponse(**response.json()).user
    assert user.username == username
    assert user.email == email.lower()
    assert user.token

    async with pool.acquire() as conn:
        user_in_db = await UsersRepository(conn).get_user_by_email(email=email)
    assert user_in_db.check_password(password)


@pytest.mark.parametrize(
    ("credentials_part", "credentials_value"),
    [("username", "free_username"), ("email", "free-email@example.com")],
)
async def test_failed_user_registration_when_some_credentials_are_taken(
    app: FastAPI,
    client: AsyncClient,
    test_user: UserInDB,
    credentials_part: str,
    credentials_value: str,
) -> None:
    registration_json = {
        "user": {
            "email": "tester@example.com",
            "username": "tester",
            "password": "password123",
        },
    }
    registration_json["user"][credentials_part] = credentials_value

    response = await client.post(app.url_path_for("auth:register"), json=registration_json)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["errors"]


@pytest.mark.parametrize(
    "invalid_user",
    [
        {"email": "not-an-email", "username": "valid_name", "password": "password123"},
        {"email": "ok@example.com", "username": "ok", "password": "password123"},
        {"email": "ok@example.com", "username": "valid name", "password": "password123"},
        {"email": "ok@example.com", "username": "valid_name", "password": "short"},
    ],
)
async def test_registration_validates_input(
    app: FastAPI,
    client: AsyncClient,
    invalid_user: dict[str, str],
) -> None:
    response = await client.post(app.url_path_for("auth:register"), json={"user": invalid_user})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["errors"]


async def test_registered_user_can_use_token_immediately(
    app: FastAPI,
    client: AsyncClient,
    make_user: Callable[..., Awaitable[UserInDB]],
) -> None:
    response = await client.post(
        app.url_path_for("auth:register"),
        json={
            "user": {"email": "new@example.com", "username": "newbie", "password": "password123"}
        },
    )
    token = response.json()["user"]["token"]

    me = await client.get(
        app.url_path_for("users:get-current-user"),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me.status_code == status.HTTP_200_OK
    assert me.json()["user"]["username"] == "newbie"
