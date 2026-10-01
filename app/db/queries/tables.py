"""Типизированные описания таблиц для построения динамических запросов на PyPika.

Статичные запросы лежат в .sql-файлах (aiosql), а запрос списка вопросов с произвольной
комбинацией фильтров собирается программно.
"""

from pypika import Parameter as CommonParameter
from pypika import Query, Table
from pypika.terms import Field


class Parameter(CommonParameter):
    """Плейсхолдер в стиле asyncpg: $1, $2, …"""

    def __init__(self, count: int) -> None:
        super().__init__(f"${count}")


class TypedTable(Table):
    __table__ = ""

    def __init__(
        self,
        name: str | None = None,
        schema: str | None = None,
        alias: str | None = None,
        query_cls: type[Query] | None = None,
    ) -> None:
        if name is None:
            name = self.__table__ or self.__class__.__name__

        super().__init__(name, schema, alias, query_cls)


# Аннотации описывают колонки как pypika.Field: во время выполнения обращение к атрибуту
# отдаёт Table.__getattr__, а mypy видит корректный тип для операций ==, ilike, as_ и т.д.
class Users(TypedTable):
    __table__ = "users"

    id: Field
    username: Field
    bio: Field
    image: Field


class Questions(TypedTable):
    __table__ = "questions"

    id: Field
    slug: Field
    title: Field
    summary: Field
    answer: Field
    grade: Field
    company: Field
    author_id: Field
    created_at: Field
    updated_at: Field


class QuestionsToTags(TypedTable):
    __table__ = "questions_to_tags"

    question_id: Field
    tag: Field


class Favorites(TypedTable):
    __table__ = "favorites"

    question_id: Field
    user_id: Field


users = Users()
authors = Users(alias="authors")
favorited_by = Users(alias="favorited_by")
questions = Questions()
questions_to_tags = QuestionsToTags()
favorites = Favorites()
