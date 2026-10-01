from collections.abc import AsyncIterator, Awaitable, Callable
from os import environ
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from asgi_lifespan import LifespanManager
from asyncpg.pool import Pool
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db.repositories.questions import QuestionsRepository
from app.db.repositories.users import UsersRepository
from app.models.domain.questions import Grade, Question
from app.models.domain.users import UserInDB
from app.services import jwt
from tests.fake_asyncpg_pool import FakeAsyncPGPool

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def _apply_migrations() -> None:
    """Перед сессией тестов схема тестовой БД пересоздаётся миграциями Alembic."""
    alembic_config = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_config.set_main_option(
        "script_location", str(PROJECT_ROOT / "app" / "db" / "migrations")
    )
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")


@pytest.fixture
def app() -> FastAPI:
    from app.main import get_application  # локальный импорт: настройки уже выставлены pytest-env

    return get_application()


@pytest.fixture
async def initialized_app(app: FastAPI) -> AsyncIterator[FastAPI]:
    async with LifespanManager(app):
        app.state.pool = await FakeAsyncPGPool.create_pool(app.state.pool)
        yield app


@pytest.fixture
def pool(initialized_app: FastAPI) -> Pool:
    fake_pool: Pool = initialized_app.state.pool
    return fake_pool


@pytest.fixture
async def client(initialized_app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=initialized_app),
        base_url="http://testserver",
        headers={"Content-Type": "application/json"},
    ) as client:
        yield client


@pytest.fixture
def authorization_prefix() -> str:
    from app.core.config import get_app_settings

    return get_app_settings().jwt_token_prefix


@pytest.fixture
def make_user(pool: Pool) -> Callable[..., Awaitable[UserInDB]]:
    async def _make_user(
        username: str,
        email: str | None = None,
        password: str = "password123",
    ) -> UserInDB:
        async with pool.acquire() as conn:
            return await UsersRepository(conn).create_user(
                username=username,
                email=email or f"{username}@example.com",
                password=password,
            )

    return _make_user


@pytest.fixture
def make_question(pool: Pool) -> Callable[..., Awaitable[Question]]:
    async def _make_question(
        author: UserInDB,
        slug: str,
        *,
        title: str | None = None,
        grade: Grade = Grade.junior,
        company: str | None = None,
        tags: list[str] | None = None,
    ) -> Question:
        async with pool.acquire() as conn:
            return await QuestionsRepository(conn).create_question(
                slug=slug,
                title=title or f"Вопрос {slug}",
                summary="Краткий контекст вопроса",
                answer="Развёрнутый ответ с примерами кода",
                grade=grade,
                company=company,
                author=author,
                tags=tags or [],
            )

    return _make_question


@pytest.fixture
async def test_user(make_user: Callable[..., Awaitable[UserInDB]]) -> UserInDB:
    return await make_user("tester", "tester@example.com")


@pytest.fixture
async def test_question(
    test_user: UserInDB,
    make_question: Callable[..., Awaitable[Question]],
) -> Question:
    return await make_question(
        test_user,
        "chto-takoe-gil",
        title="Что такое GIL?",
        company="Яндекс",
        tags=["python", "concurrency"],
    )


@pytest.fixture
def token(test_user: UserInDB) -> str:
    return jwt.create_access_token_for_user(test_user, environ["SECRET_KEY"])


@pytest.fixture
def authorized_client(client: AsyncClient, token: str, authorization_prefix: str) -> AsyncClient:
    client.headers = {"Authorization": f"{authorization_prefix} {token}", **client.headers}
    return client


def auth_headers(user: UserInDB, prefix: str = "Bearer") -> dict[str, str]:
    """Заголовок авторизации для произвольного пользователя в рамках одного теста."""
    return {
        "Authorization": f"{prefix} {jwt.create_access_token_for_user(user, environ['SECRET_KEY'])}"
    }
