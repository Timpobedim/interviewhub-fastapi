from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from asyncpg import Connection, Record
from pypika import Order, Query
from pypika import functions as fn
from pypika.queries import QueryBuilder

from app.db.errors import EntityDoesNotExistError
from app.db.queries.queries import queries
from app.db.queries.tables import (
    Parameter,
    authors,
    favorited_by,
    favorites,
    questions,
    questions_to_tags,
)
from app.db.repositories.base import BaseRepository
from app.db.repositories.profiles import ProfilesRepository
from app.db.repositories.tags import TagsRepository
from app.models.domain.profiles import Profile
from app.models.domain.questions import Grade, Question
from app.models.domain.users import User

AUTHOR_USERNAME_ALIAS = "author_username"
AUTHOR_BIO_ALIAS = "author_bio"
AUTHOR_IMAGE_ALIAS = "author_image"


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class QuestionsRepository(BaseRepository):
    def __init__(self, conn: Connection) -> None:
        super().__init__(conn)
        self._profiles_repo = ProfilesRepository(conn)
        self._tags_repo = TagsRepository(conn)

    async def create_question(
        self,
        *,
        slug: str,
        title: str,
        summary: str,
        answer: str,
        grade: Grade,
        company: str | None,
        author: User,
        tags: Sequence[str] | None = None,
    ) -> Question:
        async with self.connection.transaction():
            question_row = await queries.create_new_question(
                self.connection,
                slug=slug,
                title=title,
                summary=summary,
                answer=answer,
                grade=grade.value,
                company=company,
                author_username=author.username,
            )

            if tags:
                await self._tags_repo.create_tags_that_dont_exist(tags=tags)
                await self._link_question_with_tags(slug=slug, tags=tags)

        return await self._get_question_from_db_record(
            question_row=question_row,
            requested_user=author,
        )

    async def update_question(
        self,
        *,
        question: Question,
        changes: Mapping[str, Any],
        new_slug: str | None = None,
    ) -> Question:
        updated = question.model_copy(deep=True)
        updated.slug = new_slug or question.slug
        updated.title = changes.get("title") or question.title
        updated.summary = changes.get("summary") or question.summary
        updated.answer = changes.get("answer") or question.answer
        updated.grade = changes.get("grade") or question.grade
        if "company" in changes:
            updated.company = changes["company"]
        new_tags: list[str] | None = changes.get("tags")

        async with self.connection.transaction():
            updated.updated_at = await queries.update_question(
                self.connection,
                slug=question.slug,
                author_username=question.author.username,
                new_slug=updated.slug,
                new_title=updated.title,
                new_summary=updated.summary,
                new_answer=updated.answer,
                new_grade=updated.grade.value,
                new_company=updated.company,
            )

            if new_tags is not None:
                await queries.remove_all_tags_from_question(self.connection, slug=updated.slug)
                if new_tags:
                    await self._tags_repo.create_tags_that_dont_exist(tags=new_tags)
                    await self._link_question_with_tags(slug=updated.slug, tags=new_tags)
                updated.tags = sorted(new_tags)

        return updated

    async def delete_question(self, *, question: Question) -> None:
        async with self.connection.transaction():
            await queries.delete_question(
                self.connection,
                slug=question.slug,
                author_username=question.author.username,
            )

    async def filter_questions(
        self,
        *,
        tag: str | None = None,
        author: str | None = None,
        favorited: str | None = None,
        grade: Grade | None = None,
        company: str | None = None,
        limit: int = 20,
        offset: int = 0,
        requested_user: User | None = None,
    ) -> tuple[list[Question], int]:
        """Список вопросов с произвольной комбинацией фильтров и общее число совпадений.

        Запрос собирается на PyPika, а строковые значения фильтров
        передаются только через плейсхолдеры $N — SQL-инъекция исключена. LIMIT/OFFSET
        подставляются как числа: FastAPI уже провалидировал их как int в допустимом диапазоне.
        Отдельный COUNT-запрос с теми же фильтрами даёт честное общее количество для пагинации.
        """
        filters: dict[str, Any] = {
            "tag": tag,
            "author": author,
            "favorited": favorited,
            "grade": grade,
            "company": company,
        }

        select_query, params = self._apply_filters(self._base_select_query(), **filters)
        select_query = (
            select_query.orderby(questions.created_at, order=Order.desc)
            .orderby(questions.id, order=Order.desc)
            .limit(int(limit))
            .offset(int(offset))
        )

        count_query, count_params = self._apply_filters(
            Query.from_(questions)
            .join(authors)
            .on(questions.author_id == authors.id)
            .select(fn.Count(questions.id)),
            **filters,
        )

        rows = await self.connection.fetch(select_query.get_sql(), *params)
        total: int = await self.connection.fetchval(count_query.get_sql(), *count_params)

        return await self._build_questions(rows, requested_user=requested_user), total

    async def get_questions_for_user_feed(
        self,
        *,
        user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Question], int]:
        rows = [
            row
            async for row in queries.get_questions_for_feed(
                self.connection,
                follower_username=user.username,
                limit=limit,
                offset=offset,
            )
        ]
        total: int = await queries.count_questions_for_feed(
            self.connection,
            follower_username=user.username,
        )
        return await self._build_questions(rows, requested_user=user), total

    async def get_question_by_slug(
        self,
        *,
        slug: str,
        requested_user: User | None = None,
    ) -> Question:
        question_row = await queries.get_question_by_slug(self.connection, slug=slug)
        if question_row:
            return await self._get_question_from_db_record(
                question_row=question_row,
                requested_user=requested_user,
            )

        raise EntityDoesNotExistError(f"question with slug {slug} does not exist")

    async def add_question_into_favorites(self, *, question: Question, user: User) -> None:
        await queries.add_question_to_favorites(
            self.connection,
            username=user.username,
            slug=question.slug,
        )

    async def remove_question_from_favorites(self, *, question: Question, user: User) -> None:
        await queries.remove_question_from_favorites(
            self.connection,
            username=user.username,
            slug=question.slug,
        )

    @staticmethod
    def _base_select_query() -> QueryBuilder:
        return (
            Query.from_(questions)
            .join(authors)
            .on(questions.author_id == authors.id)
            .select(
                questions.id,
                questions.slug,
                questions.title,
                questions.summary,
                questions.answer,
                questions.grade,
                questions.company,
                questions.created_at,
                questions.updated_at,
                authors.username.as_(AUTHOR_USERNAME_ALIAS),
                authors.bio.as_(AUTHOR_BIO_ALIAS),
                authors.image.as_(AUTHOR_IMAGE_ALIAS),
            )
        )

    @staticmethod
    def _apply_filters(
        query: QueryBuilder,
        *,
        tag: str | None,
        author: str | None,
        favorited: str | None,
        grade: Grade | None,
        company: str | None,
    ) -> tuple[QueryBuilder, list[Any]]:
        params: list[Any] = []

        def next_param(value: Any) -> Parameter:
            params.append(value)
            return Parameter(len(params))

        if tag:
            query = query.join(questions_to_tags).on(
                (questions.id == questions_to_tags.question_id)
                & (questions_to_tags.tag == next_param(tag.lower())),
            )

        if favorited:
            query = (
                query.join(favorites)
                .on(questions.id == favorites.question_id)
                .join(favorited_by)
                .on(
                    (favorites.user_id == favorited_by.id)
                    & (favorited_by.username == next_param(favorited)),
                )
            )

        if author:
            query = query.where(authors.username == next_param(author))

        if grade:
            query = query.where(questions.grade == next_param(grade.value))

        if company:
            pattern = next_param(f"%{_escape_like(company)}%")
            # pypika типизирует шаблон ILIKE как str, но корректно рендерит и плейсхолдер $N
            query = query.where(questions.company.ilike(pattern))  # type: ignore[arg-type]

        return query, params

    async def _build_questions(
        self,
        rows: Sequence[Record],
        *,
        requested_user: User | None,
    ) -> list[Question]:
        """Собирает доменные объекты для страницы вопросов пакетными запросами.

        Теги, счётчик избранного и подписка на автора не грузятся отдельными запросами
        для каждого вопроса (N+1): на страницу уходит фиксированное число запросов
        независимо от её размера.
        """
        if not rows:
            return []

        question_ids = [row["id"] for row in rows]

        tags_by_question: dict[int, list[str]] = defaultdict(list)
        async for tag_row in queries.get_tags_for_questions(
            self.connection,
            question_ids=question_ids,
        ):
            tags_by_question[tag_row["question_id"]].append(tag_row["tag"])

        favorites_counts = {
            count_row["question_id"]: count_row["favorites_count"]
            async for count_row in queries.get_favorites_counts_for_questions(
                self.connection,
                question_ids=question_ids,
            )
        }

        favorited_ids: set[int] = set()
        followed_authors: set[str] = set()
        if requested_user:
            favorited_ids = {
                fav_row["question_id"]
                async for fav_row in queries.get_favorited_question_ids_for_user(
                    self.connection,
                    username=requested_user.username,
                    question_ids=question_ids,
                )
            }
            followed_authors = await self._profiles_repo.get_followed_usernames(
                requested_user=requested_user,
                usernames={row[AUTHOR_USERNAME_ALIAS] for row in rows},
            )

        return [
            Question(
                id=row["id"],
                slug=row["slug"],
                title=row["title"],
                summary=row["summary"],
                answer=row["answer"],
                grade=row["grade"],
                company=row["company"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                tags=tags_by_question.get(row["id"], []),
                author=Profile(
                    username=row[AUTHOR_USERNAME_ALIAS],
                    bio=row[AUTHOR_BIO_ALIAS],
                    image=row[AUTHOR_IMAGE_ALIAS],
                    following=row[AUTHOR_USERNAME_ALIAS] in followed_authors,
                ),
                favorited=row["id"] in favorited_ids,
                favorites_count=favorites_counts.get(row["id"], 0),
            )
            for row in rows
        ]

    async def _get_question_from_db_record(
        self,
        *,
        question_row: Record,
        requested_user: User | None,
    ) -> Question:
        built = await self._build_questions([question_row], requested_user=requested_user)
        return built[0]

    async def _link_question_with_tags(self, *, slug: str, tags: Sequence[str]) -> None:
        await queries.add_tags_to_question(
            self.connection,
            [{"slug": slug, "tag": tag} for tag in tags],
        )
