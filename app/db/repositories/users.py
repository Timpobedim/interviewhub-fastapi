from app.db.errors import EntityDoesNotExistError
from app.db.queries.queries import queries
from app.db.repositories.base import BaseRepository
from app.models.domain.users import User, UserInDB


class UsersRepository(BaseRepository):
    async def get_user_by_email(self, *, email: str) -> UserInDB:
        user_row = await queries.get_user_by_email(self.connection, email=email.lower())
        if user_row:
            return UserInDB(**user_row)

        raise EntityDoesNotExistError(f"user with email {email} does not exist")

    async def get_user_by_username(self, *, username: str) -> UserInDB:
        user_row = await queries.get_user_by_username(self.connection, username=username)
        if user_row:
            return UserInDB(**user_row)

        raise EntityDoesNotExistError(f"user with username {username} does not exist")

    async def create_user(self, *, username: str, email: str, password: str) -> UserInDB:
        user = UserInDB(username=username, email=email.lower())
        user.change_password(password)

        async with self.connection.transaction():
            user_row = await queries.create_new_user(
                self.connection,
                username=user.username,
                email=user.email,
                salt=user.salt,
                hashed_password=user.hashed_password,
            )

        return user.model_copy(
            update={
                "id_": user_row["id"],
                "created_at": user_row["created_at"],
                "updated_at": user_row["updated_at"],
            },
        )

    async def update_user(
        self,
        *,
        user: User,
        username: str | None = None,
        email: str | None = None,
        password: str | None = None,
        bio: str | None = None,
        image: str | None = None,
    ) -> UserInDB:
        user_in_db = await self.get_user_by_username(username=user.username)

        user_in_db.username = username or user_in_db.username
        user_in_db.email = (email or user_in_db.email).lower()
        user_in_db.bio = bio if bio is not None else user_in_db.bio
        user_in_db.image = image if image is not None else user_in_db.image
        if password:
            user_in_db.change_password(password)

        async with self.connection.transaction():
            user_in_db.updated_at = await queries.update_user_by_username(
                self.connection,
                username=user.username,
                new_username=user_in_db.username,
                new_email=user_in_db.email,
                new_salt=user_in_db.salt,
                new_password=user_in_db.hashed_password,
                new_bio=user_in_db.bio,
                new_image=user_in_db.image,
            )

        return user_in_db
