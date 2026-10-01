from collections.abc import Awaitable, Callable

import pytest
from asyncpg.pool import Pool
from fastapi import FastAPI
from httpx import AsyncClient
from starlette import status

from app.db.errors import EntityDoesNotExistError
from app.db.repositories.profiles import ProfilesRepository
from app.db.repositories.questions import QuestionsRepository
from app.models.domain.questions import Grade, Question
from app.models.domain.users import UserInDB
from app.models.schemas.questions import ListOfQuestionsInResponse, QuestionInResponse
from app.services.questions import get_slug_for_question
from tests.conftest import auth_headers

MakeUser = Callable[..., Awaitable[UserInDB]]
MakeQuestion = Callable[..., Awaitable[Question]]


async def test_user_can_create_question(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_user: UserInDB,
) -> None:
    title = "Чем процесс отличается от потока?"
    question_json = {
        "question": {
            "title": title,
            "summary": "Классика собеседований по ОС и Python",
            "answer": "Процесс — изолированное адресное пространство, потоки делят память…",
            "grade": "middle",
            "company": "Т-Банк",
            "tagList": ["Python", "os", "python", "  "],
        },
    }

    response = await authorized_client.post(
        app.url_path_for("questions:create-question"),
        json=question_json,
    )

    assert response.status_code == status.HTTP_201_CREATED
    question = QuestionInResponse(**response.json()).question
    assert question.slug == get_slug_for_question(title)
    assert question.slug.isascii()
    assert question.tags == ["os", "python"]
    assert question.grade == Grade.middle
    assert question.company == "Т-Банк"
    assert question.author.username == test_user.username
    assert not question.favorited
    assert question.favorites_count == 0


async def test_response_uses_camel_case_and_tag_list(
    app: FastAPI,
    client: AsyncClient,
    test_question: Question,
) -> None:
    response = await client.get(
        app.url_path_for("questions:get-question", slug=test_question.slug),
    )

    body = response.json()["question"]
    assert {"tagList", "favoritesCount", "createdAt", "updatedAt", "id"} <= body.keys()
    assert body["createdAt"].endswith("Z")


async def test_user_can_not_create_question_with_duplicated_slug(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_question: Question,
) -> None:
    question_json = {
        "question": {"title": "Что такое GIL?", "summary": "дубль", "answer": "дубль"},
    }

    response = await authorized_client.post(
        app.url_path_for("questions:create-question"),
        json=question_json,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


async def test_anonymous_user_can_not_create_question(app: FastAPI, client: AsyncClient) -> None:
    response = await client.post(
        app.url_path_for("questions:create-question"),
        json={"question": {"title": "Новый вопрос", "summary": "s", "answer": "a"}},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_user_can_not_retrieve_not_existing_question(
    app: FastAPI,
    authorized_client: AsyncClient,
) -> None:
    response = await authorized_client.get(
        app.url_path_for("questions:get-question", slug="wrong-slug"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_user_can_retrieve_question_if_exists(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_question: Question,
) -> None:
    response = await authorized_client.get(
        app.url_path_for("questions:get-question", slug=test_question.slug),
    )

    assert response.status_code == status.HTTP_200_OK
    question = QuestionInResponse(**response.json()).question
    assert question.title == test_question.title
    assert question.tags == ["concurrency", "python"]


@pytest.mark.parametrize(
    ("update_field", "update_value", "extra_updates"),
    [
        ("title", "Как устроен GIL в CPython 3.13?", {"slug": "kak-ustroen-gil-v-cpython-3-13"}),
        ("summary", "Новый контекст", {}),
        ("answer", "Новый развёрнутый ответ", {}),
        ("grade", "senior", {}),
        ("company", "Ozon", {}),
    ],
)
async def test_user_can_update_question(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_question: Question,
    update_field: str,
    update_value: str,
    extra_updates: dict[str, str],
) -> None:
    response = await authorized_client.put(
        app.url_path_for("questions:update-question", slug=test_question.slug),
        json={"question": {update_field: update_value}},
    )

    assert response.status_code == status.HTTP_200_OK
    question = QuestionInResponse(**response.json()).question.model_dump()
    assert question[update_field] == update_value
    for extra_field, extra_value in extra_updates.items():
        assert question[extra_field] == extra_value
    assert question["updated_at"] >= test_question.updated_at


async def test_user_can_replace_and_clear_tags_and_company(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_question: Question,
) -> None:
    url = app.url_path_for("questions:update-question", slug=test_question.slug)

    replaced = await authorized_client.put(
        url,
        json={"question": {"tagList": ["asyncio", "Python"], "company": None}},
    )
    cleared = await authorized_client.put(url, json={"question": {"tagList": []}})

    replaced_question = QuestionInResponse(**replaced.json()).question
    assert replaced_question.tags == ["asyncio", "python"]
    assert replaced_question.company is None
    assert QuestionInResponse(**cleared.json()).question.tags == []


async def test_user_can_not_update_question_to_existing_title(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_user: UserInDB,
    test_question: Question,
    make_question: MakeQuestion,
) -> None:
    await make_question(test_user, "chto-takoe-mro", title="Что такое MRO?")

    response = await authorized_client.put(
        app.url_path_for("questions:update-question", slug=test_question.slug),
        json={"question": {"title": "Что такое MRO?"}},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.parametrize(
    ("api_method", "route_name"),
    [("PUT", "questions:update-question"), ("DELETE", "questions:delete-question")],
)
async def test_user_can_not_modify_question_that_is_not_authored_by_him(
    app: FastAPI,
    client: AsyncClient,
    test_question: Question,
    make_user: MakeUser,
    api_method: str,
    route_name: str,
) -> None:
    stranger = await make_user("stranger")

    response = await client.request(
        api_method,
        app.url_path_for(route_name, slug=test_question.slug),
        json={"question": {"title": "Updated title"}},
        headers=auth_headers(stranger),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_user_can_delete_his_question(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_question: Question,
    pool: Pool,
) -> None:
    response = await authorized_client.delete(
        app.url_path_for("questions:delete-question", slug=test_question.slug),
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    async with pool.acquire() as connection:
        with pytest.raises(EntityDoesNotExistError):
            await QuestionsRepository(connection).get_question_by_slug(slug=test_question.slug)


@pytest.mark.parametrize(
    ("api_method", "route_name", "favorite_state"),
    [
        ("POST", "questions:mark-question-favorite", True),
        ("DELETE", "questions:unmark-question-favorite", False),
    ],
)
async def test_user_can_change_favorite_state(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_question: Question,
    test_user: UserInDB,
    pool: Pool,
    api_method: str,
    route_name: str,
    favorite_state: bool,
) -> None:
    if not favorite_state:
        async with pool.acquire() as connection:
            await QuestionsRepository(connection).add_question_into_favorites(
                question=test_question,
                user=test_user,
            )

    response = await authorized_client.request(
        api_method,
        app.url_path_for(route_name, slug=test_question.slug),
    )

    assert response.status_code == status.HTTP_200_OK
    question = QuestionInResponse(**response.json()).question
    assert question.favorited == favorite_state
    assert question.favorites_count == int(favorite_state)


@pytest.mark.parametrize(
    ("api_method", "route_name", "favorite_state"),
    [
        ("POST", "questions:mark-question-favorite", True),
        ("DELETE", "questions:unmark-question-favorite", False),
    ],
)
async def test_user_can_not_change_favorite_state_to_the_same(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_question: Question,
    test_user: UserInDB,
    pool: Pool,
    api_method: str,
    route_name: str,
    favorite_state: bool,
) -> None:
    if favorite_state:
        async with pool.acquire() as connection:
            await QuestionsRepository(connection).add_question_into_favorites(
                question=test_question,
                user=test_user,
            )

    response = await authorized_client.request(
        api_method,
        app.url_path_for(route_name, slug=test_question.slug),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


async def test_empty_list_when_nothing_is_published(app: FastAPI, client: AsyncClient) -> None:
    response = await client.get(app.url_path_for("questions:list-questions"))

    questions = ListOfQuestionsInResponse(**response.json())
    assert questions == ListOfQuestionsInResponse(questions=[], questions_count=0)


async def test_list_filters_and_total_count(
    app: FastAPI,
    client: AsyncClient,
    test_user: UserInDB,
    make_user: MakeUser,
    make_question: MakeQuestion,
    pool: Pool,
) -> None:
    other = await make_user("other")
    await make_question(test_user, "q-python-junior", tags=["python"], company="Яндекс")
    await make_question(test_user, "q-sql-middle", tags=["sql"], grade=Grade.middle)
    await make_question(other, "q-python-senior", tags=["python", "asyncio"], grade=Grade.senior)
    favorite = await make_question(other, "q-favorite", tags=["sql"], company="Ozon")
    async with pool.acquire() as connection:
        await QuestionsRepository(connection).add_question_into_favorites(
            question=favorite,
            user=test_user,
        )

    async def slugs(**params: str) -> tuple[set[str], int]:
        response = await client.get(app.url_path_for("questions:list-questions"), params=params)
        body = ListOfQuestionsInResponse(**response.json())
        return {question.slug for question in body.questions}, body.questions_count

    assert await slugs(tag="Python") == ({"q-python-junior", "q-python-senior"}, 2)
    assert await slugs(author="other") == ({"q-python-senior", "q-favorite"}, 2)
    assert await slugs(favorited="tester") == ({"q-favorite"}, 1)
    assert await slugs(grade="middle") == ({"q-sql-middle"}, 1)
    assert await slugs(company="янд") == ({"q-python-junior"}, 1)
    assert await slugs(company="100%") == (set(), 0)
    assert await slugs(tag="sql", author="other") == ({"q-favorite"}, 1)


async def test_list_pagination_returns_newest_first(
    app: FastAPI,
    client: AsyncClient,
    test_user: UserInDB,
    make_question: MakeQuestion,
) -> None:
    for index in range(5):
        await make_question(test_user, f"question-{index}")

    response = await client.get(
        app.url_path_for("questions:list-questions"),
        params={"limit": 2, "offset": 1},
    )

    body = ListOfQuestionsInResponse(**response.json())
    assert [question.slug for question in body.questions] == ["question-3", "question-2"]
    assert body.questions_count == 5


@pytest.mark.parametrize(
    "params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"grade": "lead"}]
)
async def test_list_rejects_invalid_pagination_and_filters(
    app: FastAPI,
    client: AsyncClient,
    params: dict[str, object],
) -> None:
    response = await client.get(app.url_path_for("questions:list-questions"), params=params)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


async def test_authorized_list_marks_favorites_and_following(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_user: UserInDB,
    make_user: MakeUser,
    make_question: MakeQuestion,
    pool: Pool,
) -> None:
    author = await make_user("author")
    question = await make_question(author, "saved-question")
    async with pool.acquire() as connection:
        await QuestionsRepository(connection).add_question_into_favorites(
            question=question,
            user=test_user,
        )
        await ProfilesRepository(connection).add_user_into_followers(
            target_username=author.username,
            requested_user=test_user,
        )

    response = await authorized_client.get(app.url_path_for("questions:list-questions"))

    listed = ListOfQuestionsInResponse(**response.json()).questions[0]
    assert listed.favorited
    assert listed.favorites_count == 1
    assert listed.author.following


async def test_feed_contains_only_followed_authors(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_user: UserInDB,
    make_user: MakeUser,
    make_question: MakeQuestion,
    pool: Pool,
) -> None:
    followed = await make_user("followed")
    ignored = await make_user("ignored")
    for index in range(3):
        await make_question(followed, f"followed-{index}")
    await make_question(ignored, "ignored-question")
    async with pool.acquire() as connection:
        await ProfilesRepository(connection).add_user_into_followers(
            target_username=followed.username,
            requested_user=test_user,
        )

    response = await authorized_client.get(
        app.url_path_for("questions:get-user-feed-questions"),
        params={"limit": 2},
    )

    body = ListOfQuestionsInResponse(**response.json())
    assert [question.slug for question in body.questions] == ["followed-2", "followed-1"]
    assert body.questions_count == 3
    assert all(question.author.following for question in body.questions)


async def test_feed_requires_authorization(app: FastAPI, client: AsyncClient) -> None:
    response = await client.get(app.url_path_for("questions:get-user-feed-questions"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
