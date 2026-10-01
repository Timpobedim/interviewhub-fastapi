from collections.abc import Awaitable, Callable

from asyncpg.pool import Pool
from fastapi import FastAPI
from httpx import AsyncClient
from starlette import status

from app.db.repositories.comments import CommentsRepository
from app.models.domain.questions import Question
from app.models.domain.users import UserInDB
from app.models.schemas.comments import CommentInResponse, ListOfCommentsInResponse
from tests.conftest import auth_headers


async def test_user_can_add_comment_for_question(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_question: Question,
    test_user: UserInDB,
) -> None:
    created = await authorized_client.post(
        app.url_path_for("comments:create-comment-for-question", slug=test_question.slug),
        json={"comment": {"body": "Ещё стоит упомянуть free-threaded сборку 3.13"}},
    )
    listed = await authorized_client.get(
        app.url_path_for("comments:get-comments-for-question", slug=test_question.slug),
    )

    assert created.status_code == status.HTTP_201_CREATED
    comment = CommentInResponse(**created.json()).comment
    assert comment.author.username == test_user.username
    assert ListOfCommentsInResponse(**listed.json()).comments == [comment]


async def test_anonymous_user_can_read_but_not_write_comments(
    app: FastAPI,
    client: AsyncClient,
    test_question: Question,
) -> None:
    listed = await client.get(
        app.url_path_for("comments:get-comments-for-question", slug=test_question.slug),
    )
    created = await client.post(
        app.url_path_for("comments:create-comment-for-question", slug=test_question.slug),
        json={"comment": {"body": "анонимный комментарий"}},
    )

    assert listed.status_code == status.HTTP_200_OK
    assert created.status_code == status.HTTP_401_UNAUTHORIZED


async def test_user_can_delete_own_comment(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_question: Question,
) -> None:
    created = await authorized_client.post(
        app.url_path_for("comments:create-comment-for-question", slug=test_question.slug),
        json={"comment": {"body": "комментарий"}},
    )
    comment_id = created.json()["comment"]["id"]

    deleted = await authorized_client.delete(
        app.url_path_for(
            "comments:delete-comment-from-question",
            slug=test_question.slug,
            comment_id=str(comment_id),
        ),
    )
    listed = await authorized_client.get(
        app.url_path_for("comments:get-comments-for-question", slug=test_question.slug),
    )

    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert ListOfCommentsInResponse(**listed.json()).comments == []


async def test_user_can_not_delete_not_authored_comment(
    app: FastAPI,
    client: AsyncClient,
    test_question: Question,
    test_user: UserInDB,
    make_user: Callable[..., Awaitable[UserInDB]],
    pool: Pool,
) -> None:
    stranger = await make_user("stranger")
    async with pool.acquire() as connection:
        comment = await CommentsRepository(connection).create_comment_for_question(
            body="комментарий автора",
            question=test_question,
            user=test_user,
        )

    response = await client.delete(
        app.url_path_for(
            "comments:delete-comment-from-question",
            slug=test_question.slug,
            comment_id=str(comment.id_),
        ),
        headers=auth_headers(stranger),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_user_will_receive_error_for_not_existing_comment(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_question: Question,
) -> None:
    response = await authorized_client.delete(
        app.url_path_for(
            "comments:delete-comment-from-question",
            slug=test_question.slug,
            comment_id="100500",
        ),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_comment_author_following_flag_is_resolved(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_question: Question,
    test_user: UserInDB,
    make_user: Callable[..., Awaitable[UserInDB]],
    pool: Pool,
) -> None:
    commenter = await make_user("commenter")
    async with pool.acquire() as connection:
        await CommentsRepository(connection).create_comment_for_question(
            body="мнение эксперта",
            question=test_question,
            user=commenter,
        )
    await authorized_client.post(
        app.url_path_for("profiles:follow-user", username=commenter.username),
    )

    response = await authorized_client.get(
        app.url_path_for("comments:get-comments-for-question", slug=test_question.slug),
    )

    comment = ListOfCommentsInResponse(**response.json()).comments[0]
    assert comment.author.username == commenter.username
    assert comment.author.following
