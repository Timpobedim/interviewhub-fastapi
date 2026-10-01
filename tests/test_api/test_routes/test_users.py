from collections.abc import Awaitable, Callable

import pytest
from asyncpg.pool import Pool
from fastapi import FastAPI
from httpx import AsyncClient
from starlette import status

from app.db.repositories.users import UsersRepository
from app.models.domain.users import UserInDB
from app.models.schemas.users import UserInResponse


async def test_user_can_retrieve_own_profile(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_user: UserInDB,
) -> None:
    response = await authorized_client.get(app.url_path_for("users:get-current-user"))

    assert response.status_code == status.HTTP_200_OK
    user = UserInResponse(**response.json()).user
    assert user.email == test_user.email
    assert user.username == test_user.username


@pytest.mark.parametrize(
    ("update_field", "update_value"),
    [
        ("username", "new_username"),
        ("email", "new-email@example.com"),
        ("bio", "Готовлюсь к собеседованиям на Python-разработчика"),
        ("image", "https://example.com/avatar.png"),
    ],
)
async def test_user_can_update_own_profile(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_user: UserInDB,
    update_field: str,
    update_value: str,
) -> None:
    response = await authorized_client.put(
        app.url_path_for("users:update-current-user"),
        json={"user": {update_field: update_value}},
    )

    assert response.status_code == status.HTTP_200_OK
    user_profile = UserInResponse(**response.json()).user.model_dump()
    assert user_profile[update_field] == update_value


async def test_user_can_change_password(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_user: UserInDB,
    pool: Pool,
) -> None:
    response = await authorized_client.put(
        app.url_path_for("users:update-current-user"),
        json={"user": {"password": "brand-new-password"}},
    )

    assert response.status_code == status.HTTP_200_OK
    async with pool.acquire() as connection:
        user = await UsersRepository(connection).get_user_by_username(username=test_user.username)
    assert user.check_password("brand-new-password")
    assert not user.check_password("password123")


async def test_user_can_keep_own_username_and_email(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_user: UserInDB,
) -> None:
    response = await authorized_client.put(
        app.url_path_for("users:update-current-user"),
        json={"user": {"username": test_user.username, "email": test_user.email}},
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize(
    ("credentials_part", "credentials_value"),
    [("username", "taken_username"), ("email", "taken@example.com")],
)
async def test_user_can_not_take_already_used_credentials(
    app: FastAPI,
    authorized_client: AsyncClient,
    make_user: Callable[..., Awaitable[UserInDB]],
    credentials_part: str,
    credentials_value: str,
) -> None:
    await make_user("taken_username", "taken@example.com")

    response = await authorized_client.put(
        app.url_path_for("users:update-current-user"),
        json={"user": {credentials_part: credentials_value}},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
