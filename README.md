# InterviewHub — банк вопросов с технических собеседований

REST API для сообщества, где разработчики публикуют вопросы, которые им задавали на собеседованиях,
вместе с разбором ответа, уровнем (junior / middle / senior) и компанией. Вопросы можно сохранять
в избранное, обсуждать в комментариях и следить за авторами — лента показывает новые вопросы
от тех, на кого вы подписаны.

**Стек:** Python 3.12 · FastAPI · PostgreSQL · asyncpg · aiosql (SQL в `.sql`-файлах) · PyPika ·
Alembic · Pydantic v2 · PyJWT · bcrypt · pytest · Docker · GitHub Actions.

## Что изменено и почему

- **Предметная область.** Вместо статей — вопросы с полями `grade` (уровень) и `company`;
  фильтры списка расширены: `?grade=middle&company=яндекс`. Заголовки на русском транслитерируются
  в slug: «Что такое GIL?» → `chto-takoe-gil`.
- **Без N+1.** Теги, счётчик избранного и подписка на автора не подгружаются отдельным
  запросом для каждого вопроса: страница собирается фиксированным числом пакетных
  запросов (`WHERE question_id = ANY($1)`) независимо от размера страницы.
- **Честный счётчик для пагинации.** `questionsCount` — общее число совпадений (отдельный COUNT
  с теми же фильтрами), а не длина текущей страницы.
- **Актуальные версии библиотек.** Pydantic v2 и pydantic-settings; `lifespan` вместо устаревших
  обработчиков startup/shutdown; aiosql 15 — явные сигнатуры параметров в именах запросов и
  асинхронные генераторы для многострочных SELECT; ruff вместо black + isort + wemake;
  uv вместо Poetry.
- **Семантика ошибок.** Отсутствующий или неверный токен — `401` с заголовком `WWW-Authenticate`,
  попытка изменить чужой вопрос — `403`. Схема токена — стандартный `Bearer`.
- **Пароли.** bcrypt учитывает только 72 байта (а bcrypt ≥ 5 падает на более длинном вводе),
  поэтому пароль с солью предварительно сворачивается в SHA-256 — длина пароля не ограничена.

## API

Все маршруты — под префиксом `/api`. Интерактивная документация: `/docs` (Swagger) и `/redoc`.

| Метод | Путь | Доступ | Назначение |
|---|---|---|---|
| POST | `/users` | все | Регистрация |
| POST | `/users/login` | все | Вход, выдаёт JWT |
| GET / PUT | `/user` | авторизованные | Текущий пользователь / обновление профиля |
| GET | `/profiles/{username}` | все | Профиль автора |
| POST / DELETE | `/profiles/{username}/follow` | авторизованные | Подписаться / отписаться |
| GET | `/questions` | все | Список: `tag`, `author`, `favorited`, `grade`, `company`, `limit`, `offset` |
| GET | `/questions/feed` | авторизованные | Вопросы авторов из подписок |
| POST | `/questions` | авторизованные | Опубликовать вопрос |
| GET / PUT / DELETE | `/questions/{slug}` | все / автор / автор | Получить / изменить / удалить |
| POST / DELETE | `/questions/{slug}/favorite` | авторизованные | Сохранить в избранное / убрать |
| GET / POST | `/questions/{slug}/comments` | все / авторизованные | Обсуждение вопроса |
| DELETE | `/questions/{slug}/comments/{id}` | автор комментария | Удалить комментарий |
| GET | `/tags` | все | Все технологии-теги |
| GET | `/health` | все | Проверка доступности БД |

Пример запроса:

```bash
curl -X POST http://localhost:8000/api/questions \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"question": {"title": "Что такое MRO?", "summary": "ООП в Python",
       "answer": "Порядок разрешения методов, алгоритм C3…", "grade": "middle",
       "company": "Ozon", "tagList": ["python", "oop"]}}'
```

## Быстрый старт

### Docker

```bash
docker compose up --build
# API: http://localhost:8000/docs
docker compose exec app python -m scripts.seed   # демо-данные: 3 автора, 12 вопросов
```

### Локально

```bash
cp .env.example .env              # укажите DATABASE_URL своего PostgreSQL
uv sync --group dev
uv run alembic upgrade head
uv run python -m scripts.seed     # необязательно: демо-данные
uv run uvicorn app.main:app --reload
```

Демо-аккаунты создаются с паролем `demo-password`: `anna_backend@interviewhub.dev`,
`dmitry_sql@interviewhub.dev`, `junior_ivan@interviewhub.dev`.

## Тесты и качество кода

Тесты работают с настоящим PostgreSQL: перед сессией схема пересоздаётся миграциями, а каждый тест
выполняется в транзакции, которая откатывается в конце.

```bash
# нужна пустая БД interviewhub_test (строка подключения — в pyproject.toml, секция pytest env)
uv run pytest                     # 86 тестов, покрытие ~99,7 %, порог в CI — 95 %
uv run ruff check . && uv run ruff format --check .
uv run mypy app
```

В CI (`.github/workflows/`) два пайплайна: `tests` поднимает PostgreSQL как service-контейнер,
`styles` проверяет линтер, форматирование и типы.

## Структура

```
app/
├── api/
│   ├── dependencies/      # репозитории, авторизация, загрузка сущностей из пути
│   ├── errors/            # единый формат ошибок {"errors": [...]}
│   └── routes/            # маршруты; questions/ разделён на common (лента, избранное) и resource (CRUD)
├── core/                  # настройки по окружениям, lifespan, логирование через loguru
├── db/
│   ├── migrations/        # Alembic
│   ├── queries/           # .sql-файлы aiosql, PyPika-таблицы, .pyi-стаб
│   └── repositories/      # доступ к данным
├── models/
│   ├── domain/            # доменные модели
│   └── schemas/           # схемы запросов и ответов API
├── resources/strings.py   # тексты ошибок
└── services/              # JWT, хеширование паролей, slug, проверки прав
scripts/seed.py            # демо-данные
tests/                     # API-тесты по маршрутам + юнит-тесты сервисов
```

## Идеи для развития

- Полнотекстовый поиск по вопросам (`tsvector` + GIN-индекс, русская морфология).
- Голосование за лучший ответ в комментариях и сортировка по рейтингу.
- Режим тренировки: случайный вопрос по выбранным тегам и уровню, отметка «знаю / не знаю».
- Кеширование списка тегов и популярных вопросов в Redis.
