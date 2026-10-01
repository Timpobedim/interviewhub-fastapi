import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette import status

from app.models.domain.users import UserInDB
from app.models.schemas.users import UserInResponse


async def test_user_successful_login(
    app: FastAPI, client: AsyncClient, test_user: UserInDB
) -> None:
    login_json = {"user": {"email": "tester@example.com", "password": "password123"}}

    response = await client.post(app.url_path_for("auth:login"), json=login_json)

    assert response.status_code == status.HTTP_200_OK
    user = UserInResponse(**response.json()).user
    assert user.username == test_user.username
    assert user.token


async def test_login_is_case_insensitive_for_email(
    app: FastAPI,
    client: AsyncClient,
    test_user: UserInDB,
) -> None:
    login_json = {"user": {"email": "TESTER@example.com", "password": "password123"}}

    response = await client.post(app.url_path_for("auth:login"), json=login_json)

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize(
    ("email", "password"),
    [("wrong@example.com", "password123"), ("tester@example.com", "wrong-password")],
)
async def test_user_login_when_credential_part_does_not_match(
    app: FastAPI,
    client: AsyncClient,
    test_user: UserInDB,
    email: str,
    password: str,
) -> None:
    login_json = {"user": {"email": email, "password": password}}

    response = await client.post(app.url_path_for("auth:login"), json=login_json)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"errors": ["неверный email или пароль"]}
