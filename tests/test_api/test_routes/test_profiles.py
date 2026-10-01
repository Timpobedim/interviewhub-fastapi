from collections.abc import Awaitable, Callable

from asyncpg.pool import Pool
from fastapi import FastAPI
from httpx import AsyncClient
from starlette import status

from app.db.repositories.profiles import ProfilesRepository
from app.models.domain.users import UserInDB
from app.models.schemas.profiles import ProfileInResponse


async def test_unregistered_user_can_retrieve_profile(
    app: FastAPI,
    client: AsyncClient,
    test_user: UserInDB,
) -> None:
    response = await client.get(
        app.url_path_for("profiles:get-profile", username=test_user.username),
    )

    assert response.status_code == status.HTTP_200_OK
    profile = ProfileInResponse(**response.json()).profile
    assert profile.username == test_user.username
    assert not profile.following


async def test_user_receives_404_for_unknown_profile(app: FastAPI, client: AsyncClient) -> None:
    response = await client.get(app.url_path_for("profiles:get-profile", username="nobody"))

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_user_can_follow_and_unfollow_another_user(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_user: UserInDB,
    make_user: Callable[..., Awaitable[UserInDB]],
    pool: Pool,
) -> None:
    author = await make_user("author")
    url = app.url_path_for("profiles:follow-user", username=author.username)

    follow_response = await authorized_client.post(url)
    profile_response = await authorized_client.get(
        app.url_path_for("profiles:get-profile", username=author.username),
    )
    unfollow_response = await authorized_client.delete(
        app.url_path_for("profiles:unsubscribe-from-user", username=author.username),
    )

    assert follow_response.status_code == status.HTTP_200_OK
    assert ProfileInResponse(**follow_response.json()).profile.following
    assert ProfileInResponse(**profile_response.json()).profile.following
    assert unfollow_response.status_code == status.HTTP_200_OK
    assert not ProfileInResponse(**unfollow_response.json()).profile.following

    async with pool.acquire() as conn:
        is_following = await ProfilesRepository(conn).is_user_following_for_another_user(
            target_username=author.username,
            requested_user=test_user,
        )
    assert not is_following


async def test_user_can_not_follow_twice_or_unfollow_not_followed(
    app: FastAPI,
    authorized_client: AsyncClient,
    make_user: Callable[..., Awaitable[UserInDB]],
) -> None:
    author = await make_user("author")
    follow_url = app.url_path_for("profiles:follow-user", username=author.username)

    not_followed = await authorized_client.delete(follow_url)
    await authorized_client.post(follow_url)
    followed_twice = await authorized_client.post(follow_url)

    assert not_followed.status_code == status.HTTP_400_BAD_REQUEST
    assert followed_twice.status_code == status.HTTP_400_BAD_REQUEST


async def test_user_can_not_follow_or_unfollow_self(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_user: UserInDB,
) -> None:
    url = app.url_path_for("profiles:follow-user", username=test_user.username)

    follow_self = await authorized_client.post(url)
    unfollow_self = await authorized_client.delete(url)

    assert follow_self.status_code == status.HTTP_400_BAD_REQUEST
    assert unfollow_self.status_code == status.HTTP_400_BAD_REQUEST
