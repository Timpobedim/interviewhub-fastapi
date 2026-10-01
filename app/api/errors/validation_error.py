from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

HTTP_422_UNPROCESSABLE_CONTENT = 422


async def http422_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError | ValidationError)  # noqa: S101
    # jsonable_encoder: в pydantic v2 errors() может содержать объекты исключений в ctx.
    return JSONResponse(
        {"errors": jsonable_encoder(exc.errors())},
        status_code=HTTP_422_UNPROCESSABLE_CONTENT,
    )
