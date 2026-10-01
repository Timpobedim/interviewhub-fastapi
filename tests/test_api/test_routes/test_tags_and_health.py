from fastapi import FastAPI
from httpx import AsyncClient
from starlette import status

from app.models.domain.questions import Question
from app.models.schemas.tags import TagsInList


async def test_empty_list_when_there_are_no_tags(app: FastAPI, client: AsyncClient) -> None:
    response = await client.get(app.url_path_for("tags:get-all"))

    assert TagsInList(**response.json()) == TagsInList(tags=[])


async def test_tags_of_created_questions_are_listed_sorted(
    app: FastAPI,
    client: AsyncClient,
    test_question: Question,
) -> None:
    response = await client.get(app.url_path_for("tags:get-all"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"tags": ["concurrency", "python"]}


async def test_health_check_pings_database(app: FastAPI, client: AsyncClient) -> None:
    response = await client.get(app.url_path_for("health:check"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}
