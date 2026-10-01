from fastapi import FastAPI
from httpx import AsyncClient
from starlette import status


async def test_frw_validation_error_format(app: FastAPI, client: AsyncClient) -> None:
    response = await client.post(app.url_path_for("auth:login"), json={"user": {"email": 1}})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    errors = response.json()["errors"]
    assert isinstance(errors, list)
    assert {"loc", "msg", "type"} <= errors[0].keys()


async def test_frw_not_found_error_format(client: AsyncClient) -> None:
    response = await client.get("/api/definitely-not-a-route")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"errors": ["Not Found"]}
