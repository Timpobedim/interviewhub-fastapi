"""Типизация запросов, которые aiosql генерирует из .sql-файлов.

Суффиксы операций: «^» — одна строка, «$» — скалярное значение, «!» — изменение без
результата, «<!» — INSERT/UPDATE ... RETURNING, «*!» — пакетное выполнение. SELECT без суффикса
в aiosql ≥ 10 возвращает асинхронный генератор, поэтому он объявлен как обычный метод.
"""

from collections.abc import AsyncIterator, Sequence
from datetime import datetime

from asyncpg import Connection, Record

class Queries:
    # users.sql
    async def get_user_by_email(self, conn: Connection, *, email: str) -> Record | None: ...
    async def get_user_by_username(self, conn: Connection, *, username: str) -> Record | None: ...
    async def create_new_user(
        self,
        conn: Connection,
        *,
        username: str,
        email: str,
        salt: str,
        hashed_password: str,
    ) -> Record: ...
    async def update_user_by_username(
        self,
        conn: Connection,
        *,
        username: str,
        new_username: str,
        new_email: str,
        new_salt: str,
        new_password: str,
        new_bio: str,
        new_image: str | None,
    ) -> datetime: ...

    # profiles.sql
    async def is_user_following_for_another_user(
        self,
        conn: Connection,
        *,
        follower_username: str,
        following_username: str,
    ) -> bool: ...
    async def subscribe_user_to_another(
        self,
        conn: Connection,
        *,
        follower_username: str,
        following_username: str,
    ) -> None: ...
    async def unsubscribe_user_from_another(
        self,
        conn: Connection,
        *,
        follower_username: str,
        following_username: str,
    ) -> None: ...
    def get_followed_usernames_among(
        self,
        conn: Connection,
        *,
        follower_username: str,
        usernames: Sequence[str],
    ) -> AsyncIterator[Record]: ...

    # tags.sql
    def get_all_tags(self, conn: Connection) -> AsyncIterator[Record]: ...
    async def create_new_tags(self, conn: Connection, tags: Sequence[dict[str, str]]) -> None: ...

    # questions.sql
    async def get_question_by_slug(self, conn: Connection, *, slug: str) -> Record | None: ...
    async def create_new_question(
        self,
        conn: Connection,
        *,
        slug: str,
        title: str,
        summary: str,
        answer: str,
        grade: str,
        company: str | None,
        author_username: str,
    ) -> Record: ...
    async def add_tags_to_question(
        self,
        conn: Connection,
        tags: Sequence[dict[str, str]],
    ) -> None: ...
    async def remove_all_tags_from_question(self, conn: Connection, *, slug: str) -> None: ...
    async def update_question(
        self,
        conn: Connection,
        *,
        slug: str,
        author_username: str,
        new_slug: str,
        new_title: str,
        new_summary: str,
        new_answer: str,
        new_grade: str,
        new_company: str | None,
    ) -> datetime: ...
    async def delete_question(
        self, conn: Connection, *, slug: str, author_username: str
    ) -> None: ...
    async def add_question_to_favorites(
        self,
        conn: Connection,
        *,
        username: str,
        slug: str,
    ) -> None: ...
    async def remove_question_from_favorites(
        self,
        conn: Connection,
        *,
        username: str,
        slug: str,
    ) -> None: ...
    def get_tags_for_questions(
        self,
        conn: Connection,
        *,
        question_ids: Sequence[int],
    ) -> AsyncIterator[Record]: ...
    def get_favorites_counts_for_questions(
        self,
        conn: Connection,
        *,
        question_ids: Sequence[int],
    ) -> AsyncIterator[Record]: ...
    def get_favorited_question_ids_for_user(
        self,
        conn: Connection,
        *,
        username: str,
        question_ids: Sequence[int],
    ) -> AsyncIterator[Record]: ...
    def get_questions_for_feed(
        self,
        conn: Connection,
        *,
        follower_username: str,
        limit: int,
        offset: int,
    ) -> AsyncIterator[Record]: ...
    async def count_questions_for_feed(
        self,
        conn: Connection,
        *,
        follower_username: str,
    ) -> int: ...

    # comments.sql
    def get_comments_for_question_by_slug(
        self,
        conn: Connection,
        *,
        slug: str,
    ) -> AsyncIterator[Record]: ...
    async def get_comment_by_id_and_slug(
        self,
        conn: Connection,
        *,
        comment_id: int,
        question_slug: str,
    ) -> Record | None: ...
    async def create_new_comment(
        self,
        conn: Connection,
        *,
        body: str,
        question_slug: str,
        author_username: str,
    ) -> Record: ...
    async def delete_comment_by_id(
        self,
        conn: Connection,
        *,
        comment_id: int,
        author_username: str,
    ) -> None: ...

queries: Queries
