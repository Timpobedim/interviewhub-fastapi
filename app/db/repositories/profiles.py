from collections.abc import Collection

from asyncpg import Connection

from app.db.queries.queries import queries
from app.db.repositories.base import BaseRepository
from app.db.repositories.users import UsersRepository
from app.models.domain.profiles import Profile
from app.models.domain.users import User


class ProfilesRepository(BaseRepository):
    def __init__(self, conn: Connection) -> None:
        super().__init__(conn)
        self._users_repo = UsersRepository(conn)

    async def get_profile_by_username(
        self,
        *,
        username: str,
        requested_user: User | None,
    ) -> Profile:
        user = await self._users_repo.get_user_by_username(username=username)

        profile = Profile(username=user.username, bio=user.bio, image=user.image)
        if requested_user:
            profile.following = await self.is_user_following_for_another_user(
                target_username=user.username,
                requested_user=requested_user,
            )

        return profile

    async def is_user_following_for_another_user(
        self,
        *,
        target_username: str,
        requested_user: User,
    ) -> bool:
        is_following: bool = await queries.is_user_following_for_another_user(
            self.connection,
            follower_username=requested_user.username,
            following_username=target_username,
        )
        return is_following

    async def add_user_into_followers(self, *, target_username: str, requested_user: User) -> None:
        async with self.connection.transaction():
            await queries.subscribe_user_to_another(
                self.connection,
                follower_username=requested_user.username,
                following_username=target_username,
            )

    async def remove_user_from_followers(
        self,
        *,
        target_username: str,
        requested_user: User,
    ) -> None:
        async with self.connection.transaction():
            await queries.unsubscribe_user_from_another(
                self.connection,
                follower_username=requested_user.username,
                following_username=target_username,
            )

    async def get_followed_usernames(
        self,
        *,
        requested_user: User,
        usernames: Collection[str],
    ) -> set[str]:
        """Возвращает подмножество usernames, на которых подписан requested_user (один запрос)."""
        if not usernames:
            return set()

        return {
            row["username"]
            async for row in queries.get_followed_usernames_among(
                self.connection,
                follower_username=requested_user.username,
                usernames=list(usernames),
            )
        }
