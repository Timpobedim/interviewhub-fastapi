from collections.abc import Sequence

from asyncpg import Connection, Record

from app.db.errors import EntityDoesNotExistError
from app.db.queries.queries import queries
from app.db.repositories.base import BaseRepository
from app.db.repositories.profiles import ProfilesRepository
from app.models.domain.comments import Comment
from app.models.domain.profiles import Profile
from app.models.domain.questions import Question
from app.models.domain.users import User


class CommentsRepository(BaseRepository):
    def __init__(self, conn: Connection) -> None:
        super().__init__(conn)
        self._profiles_repo = ProfilesRepository(conn)

    async def get_comment_by_id(
        self,
        *,
        comment_id: int,
        question: Question,
        user: User | None = None,
    ) -> Comment:
        comment_row = await queries.get_comment_by_id_and_slug(
            self.connection,
            comment_id=comment_id,
            question_slug=question.slug,
        )
        if comment_row:
            return (await self._build_comments([comment_row], user=user))[0]

        raise EntityDoesNotExistError(
            f"comment with id {comment_id} does not exist for question {question.slug}",
        )

    async def get_comments_for_question(
        self,
        *,
        question: Question,
        user: User | None = None,
    ) -> list[Comment]:
        comments_rows = [
            row
            async for row in queries.get_comments_for_question_by_slug(
                self.connection,
                slug=question.slug,
            )
        ]
        return await self._build_comments(comments_rows, user=user)

    async def create_comment_for_question(
        self,
        *,
        body: str,
        question: Question,
        user: User,
    ) -> Comment:
        comment_row = await queries.create_new_comment(
            self.connection,
            body=body,
            question_slug=question.slug,
            author_username=user.username,
        )
        return (await self._build_comments([comment_row], user=user))[0]

    async def delete_comment(self, *, comment: Comment) -> None:
        await queries.delete_comment_by_id(
            self.connection,
            comment_id=comment.id_,
            author_username=comment.author.username,
        )

    async def _build_comments(self, rows: Sequence[Record], *, user: User | None) -> list[Comment]:
        followed_authors: set[str] = set()
        if user and rows:
            followed_authors = await self._profiles_repo.get_followed_usernames(
                requested_user=user,
                usernames={row["author_username"] for row in rows},
            )

        return [
            Comment(
                id=row["id"],
                body=row["body"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                author=Profile(
                    username=row["author_username"],
                    bio=row["author_bio"],
                    image=row["author_image"],
                    following=row["author_username"] in followed_authors,
                ),
            )
            for row in rows
        ]
