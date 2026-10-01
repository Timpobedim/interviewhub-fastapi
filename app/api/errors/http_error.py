from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse


async def http_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)  # noqa: S101 — обработчик зарегистрирован для HTTPException
    return JSONResponse(
        {"errors": [exc.detail]},
        status_code=exc.status_code,
        headers=exc.headers,
    )
