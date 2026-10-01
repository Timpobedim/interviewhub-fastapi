from fastapi import APIRouter, Body, Depends, HTTPException
from starlette import status

from app.api.dependencies.database import get_repository
from app.core.config import get_app_settings
from app.core.settings.app import AppSettings
from app.db.errors import EntityDoesNotExistError
from app.db.repositories.users import UsersRepository
from app.models.domain.users import User
from app.models.schemas.users import UserInCreate, UserInLogin, UserInResponse, UserWithToken
from app.resources import strings
from app.services import jwt
from app.services.authentication import check_email_is_taken, check_username_is_taken

router = APIRouter()


def build_user_response(user: User, settings: AppSettings) -> UserInResponse:
    token = jwt.create_access_token_for_user(
        user,
        settings.secret_key.get_secret_value(),
        settings.access_token_expire_minutes,
    )
    return UserInResponse(
        user=UserWithToken(
            username=user.username,
            email=user.email,
            bio=user.bio,
            image=user.image,
            token=token,
        ),
    )


@router.post("/login", response_model=UserInResponse, name="auth:login")
async def login(
    user_login: UserInLogin = Body(..., embed=True, alias="user"),
    users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
    settings: AppSettings = Depends(get_app_settings),
) -> UserInResponse:
    wrong_login_error = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=strings.INCORRECT_LOGIN_INPUT,
    )

    try:
        user = await users_repo.get_user_by_email(email=user_login.email)
    except EntityDoesNotExistError as existence_error:
        raise wrong_login_error from existence_error

    if not user.check_password(user_login.password):
        raise wrong_login_error

    return build_user_response(user, settings)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=UserInResponse,
    name="auth:register",
)
async def register(
    user_create: UserInCreate = Body(..., embed=True, alias="user"),
    users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
    settings: AppSettings = Depends(get_app_settings),
) -> UserInResponse:
    if await check_username_is_taken(users_repo, user_create.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=strings.USERNAME_TAKEN,
        )

    if await check_email_is_taken(users_repo, user_create.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=strings.EMAIL_TAKEN,
        )

    user = await users_repo.create_user(
        username=user_create.username,
        email=user_create.email,
        password=user_create.password,
    )
    return build_user_response(user, settings)
