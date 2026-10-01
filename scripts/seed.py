"""Наполняет базу демонстрационными данными: авторы, вопросы с собеседований, подписки, избранное.

Запуск (после «alembic upgrade head»):  python -m scripts.seed
Скрипт идемпотентен: существующие пользователи и вопросы пропускаются.
"""

import asyncio
from dataclasses import dataclass, field

import asyncpg
from loguru import logger

from app.core.config import get_app_settings
from app.db.errors import EntityDoesNotExistError
from app.db.repositories.comments import CommentsRepository
from app.db.repositories.profiles import ProfilesRepository
from app.db.repositories.questions import QuestionsRepository
from app.db.repositories.users import UsersRepository
from app.models.domain.questions import Grade
from app.models.domain.users import UserInDB
from app.services.questions import get_slug_for_question

DEMO_PASSWORD = "demo-password"  # noqa: S105 — пароль демо-аккаунтов из README


@dataclass(frozen=True)
class SeedQuestion:
    author: str
    title: str
    summary: str
    answer: str
    grade: Grade
    tags: list[str]
    company: str | None = None
    saved_by: list[str] = field(default_factory=list)


USERS = {
    "anna_backend": "Python-разработчик, провожу технические собеседования",
    "dmitry_sql": "Аналитик данных, собираю вопросы по SQL",
    "junior_ivan": "Готовлюсь к первому собеседованию на Junior Python",
}

QUESTIONS = [
    SeedQuestion(
        author="anna_backend",
        title="Что такое GIL и почему он мешает многопоточности в CPython?",
        summary="Классический вопрос про конкурентность в Python.",
        answer=(
            "GIL (Global Interpreter Lock) — мьютекс интерпретатора CPython: в каждый момент "
            "байт-код выполняет только один поток. Для CPU-bound задач потоки не дают прироста — "
            "используют multiprocessing или C-расширения, отпускающие GIL. Для I/O-bound задач "
            "потоки работают нормально: GIL освобождается на время ожидания ввода-вывода. "
            "С Python 3.13 есть экспериментальная free-threaded сборка без GIL (PEP 703)."
        ),
        grade=Grade.junior,
        tags=["python", "concurrency"],
        company="Яндекс",
        saved_by=["junior_ivan"],
    ),
    SeedQuestion(
        author="anna_backend",
        title="Чем list отличается от tuple?",
        summary="Проверка базовых типов данных.",
        answer=(
            "list изменяемый, tuple — нет. Кортеж можно использовать как ключ словаря, если все "
            "его элементы хешируемы; он занимает меньше памяти и чуть быстрее создаётся. "
            "Семантически tuple — запись фиксированной структуры, list — коллекция однотипных "
            "элементов переменной длины."
        ),
        grade=Grade.junior,
        tags=["python"],
        saved_by=["junior_ivan"],
    ),
    SeedQuestion(
        author="anna_backend",
        title="Как работают декораторы в Python?",
        summary="Функции высшего порядка и замыкания.",
        answer=(
            "Декоратор — вызываемый объект, который принимает функцию и возвращает новую. "
            "Запись @decorator над def f — сахар для f = decorator(f). Обёртку оформляют через "
            "functools.wraps, чтобы сохранить имя и docstring. Декоратор с параметрами — это "
            "фабрика: функция, возвращающая декоратор."
        ),
        grade=Grade.junior,
        tags=["python"],
        company="Т-Банк",
    ),
    SeedQuestion(
        author="anna_backend",
        title="Что такое MRO и как Python ищет метод при множественном наследовании?",
        summary="Порядок разрешения методов и алгоритм C3.",
        answer=(
            "MRO (Method Resolution Order) — линейный порядок классов, в котором ищется атрибут. "
            "Python строит его алгоритмом C3-линеаризации: потомок раньше предков, порядок "
            "базовых классов сохраняется. Посмотреть можно через Class.__mro__, а super() "
            "вызывает следующий класс именно по MRO, а не «родителя»."
        ),
        grade=Grade.middle,
        tags=["python", "oop"],
    ),
    SeedQuestion(
        author="anna_backend",
        title="Чем asyncio отличается от потоков и когда что выбирать?",
        summary="Кооперативная многозадачность против вытесняющей.",
        answer=(
            "asyncio — однопоточный цикл событий: корутины сами уступают управление на await. "
            "Переключения дешёвые, поэтому тысячи одновременных I/O-операций обслуживаются без "
            "потоков. Потоки переключает ОС в любой момент — нужны блокировки. Выбор: много "
            "сетевых соединений и async-библиотеки — asyncio; блокирующие библиотеки — потоки "
            "(или asyncio.to_thread); тяжёлые вычисления — процессы."
        ),
        grade=Grade.middle,
        tags=["python", "asyncio", "concurrency"],
        company="Ozon",
        saved_by=["junior_ivan", "dmitry_sql"],
    ),
    SeedQuestion(
        author="dmitry_sql",
        title="Чем INNER JOIN отличается от LEFT JOIN?",
        summary="Вопрос, который задают почти на каждом собеседовании аналитика.",
        answer=(
            "INNER JOIN возвращает только строки, для которых нашлось совпадение в обеих "
            "таблицах. LEFT JOIN возвращает все строки левой таблицы, а для строк без пары "
            "подставляет NULL в колонки правой. Типичная ошибка — условие на правую таблицу "
            "в WHERE, которое превращает LEFT JOIN в INNER: такое условие переносят в ON."
        ),
        grade=Grade.junior,
        tags=["sql"],
        company="Сбер",
        saved_by=["junior_ivan"],
    ),
    SeedQuestion(
        author="dmitry_sql",
        title="Как работают оконные функции в SQL? Пример с ROW_NUMBER",
        summary="Аналитика без схлопывания строк.",
        answer=(
            "Оконная функция считает значение по набору строк, связанных с текущей, не "
            "группируя их. Пример — последний заказ каждого клиента: ROW_NUMBER() OVER "
            "(PARTITION BY client_id ORDER BY created_at DESC) AS rn, затем фильтр rn = 1 "
            "во внешнем запросе. Другие частые функции: RANK, LAG/LEAD, SUM() OVER для "
            "накопительного итога."
        ),
        grade=Grade.middle,
        tags=["sql", "postgresql"],
        company="Авито",
    ),
    SeedQuestion(
        author="dmitry_sql",
        title="Что такое индекс в PostgreSQL и когда он не поможет?",
        summary="B-tree, селективность и план запроса.",
        answer=(
            "Индекс — отдельная структура (по умолчанию B-tree), ускоряющая поиск по колонкам. "
            "Он не поможет при низкой селективности (запрос возвращает большую долю таблицы), "
            "при функции над колонкой без функционального индекса, при LIKE '%текст' и при "
            "несовпадении типов. Индексы замедляют запись. Проверять — через EXPLAIN ANALYZE."
        ),
        grade=Grade.middle,
        tags=["sql", "postgresql"],
    ),
    SeedQuestion(
        author="dmitry_sql",
        title="Какие уровни изоляции транзакций существуют и от каких аномалий они защищают?",
        summary="ACID и стандарт SQL на практике PostgreSQL.",
        answer=(
            "Read Uncommitted, Read Committed, Repeatable Read, Serializable защищают от грязного "
            "чтения, неповторяющегося чтения, фантомов и аномалий сериализации соответственно. "
            "В PostgreSQL по умолчанию Read Committed, грязного чтения нет вовсе, а Repeatable "
            "Read реализован снимком данных и не допускает фантомов."
        ),
        grade=Grade.senior,
        tags=["sql", "postgresql", "transactions"],
        company="Яндекс",
    ),
    SeedQuestion(
        author="anna_backend",
        title="Чем git merge отличается от git rebase?",
        summary="История коммитов и командная работа.",
        answer=(
            "merge объединяет ветки коммитом слияния и сохраняет историю как есть. rebase "
            "переносит коммиты ветки поверх другой, переписывая их хеши: история получается "
            "линейной. Золотое правило — не делать rebase публичных веток, с которыми работают "
            "другие."
        ),
        grade=Grade.junior,
        tags=["git"],
    ),
    SeedQuestion(
        author="anna_backend",
        title="Что происходит, когда вы вводите адрес сайта в браузере?",
        summary="Сквозной вопрос про сети и веб.",
        answer=(
            "Браузер разбирает URL, находит IP через DNS (кеш браузера, ОС, резолвер), "
            "устанавливает TCP-соединение и TLS-сессию для HTTPS, отправляет HTTP-запрос. "
            "Сервер (часто за балансировщиком и reverse proxy) возвращает ответ, браузер строит "
            "DOM и CSSOM, загружает ресурсы, выполняет JavaScript и отрисовывает страницу."
        ),
        grade=Grade.junior,
        tags=["http", "networks"],
        company="VK",
    ),
    SeedQuestion(
        author="anna_backend",
        title="Что такое идемпотентность HTTP-методов?",
        summary="Проектирование REST API.",
        answer=(
            "Метод идемпотентен, если повтор запроса оставляет сервер в том же состоянии, что "
            "и один запрос. GET, PUT, DELETE идемпотентны, POST — нет. Это важно для ретраев: "
            "идемпотентные запросы можно безопасно повторять, для POST используют ключ "
            "идемпотентности (Idempotency-Key)."
        ),
        grade=Grade.middle,
        tags=["http", "rest"],
    ),
]

FOLLOWS = [
    ("junior_ivan", "anna_backend"),
    ("junior_ivan", "dmitry_sql"),
    ("anna_backend", "dmitry_sql"),
]

COMMENTS = [
    (
        "Что такое GIL и почему он мешает многопоточности в CPython?",
        "junior_ivan",
        "Спросили ровно это на первом собеседовании, ответ помог!",
    ),
    (
        "Чем INNER JOIN отличается от LEFT JOIN?",
        "anna_backend",
        "Хорошо бы добавить FULL OUTER JOIN для полноты.",
    ),
]


async def _get_or_create_user(users: UsersRepository, username: str, bio: str) -> UserInDB:
    try:
        return await users.get_user_by_username(username=username)
    except EntityDoesNotExistError:
        user = await users.create_user(
            username=username,
            email=f"{username}@interviewhub.dev",
            password=DEMO_PASSWORD,
        )
        return await users.update_user(user=user, bio=bio)


async def seed() -> None:
    settings = get_app_settings()
    connection = await asyncpg.connect(settings.database_dsn)
    try:
        users_repo = UsersRepository(connection)
        questions_repo = QuestionsRepository(connection)
        profiles_repo = ProfilesRepository(connection)
        comments_repo = CommentsRepository(connection)

        users = {
            name: await _get_or_create_user(users_repo, name, bio) for name, bio in USERS.items()
        }

        for follower, following in FOLLOWS:
            await profiles_repo.add_user_into_followers(
                target_username=following,
                requested_user=users[follower],
            )

        created = 0
        for item in QUESTIONS:
            slug = get_slug_for_question(item.title)
            try:
                question = await questions_repo.get_question_by_slug(slug=slug)
            except EntityDoesNotExistError:
                question = await questions_repo.create_question(
                    slug=slug,
                    title=item.title,
                    summary=item.summary,
                    answer=item.answer,
                    grade=item.grade,
                    company=item.company,
                    author=users[item.author],
                    tags=item.tags,
                )
                created += 1
                for username in item.saved_by:
                    await questions_repo.add_question_into_favorites(
                        question=question,
                        user=users[username],
                    )

        if created:
            by_title = {item.title: get_slug_for_question(item.title) for item in QUESTIONS}
            for title, username, body in COMMENTS:
                question = await questions_repo.get_question_by_slug(slug=by_title[title])
                await comments_repo.create_comment_for_question(
                    body=body,
                    question=question,
                    user=users[username],
                )

        logger.info("Готово: пользователей {}, новых вопросов {}", len(users), created)
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(seed())
