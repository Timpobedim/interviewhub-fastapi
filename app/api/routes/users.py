from fastapi import APIRouter, Body, Depends, HTTPException
from starlette import status

from app.api.dependencies.authentication import get_current_user_authorizer
from app.api.dependencies.database import get_repository
from app.api.routes.authentication import build_user_response
from app.core.config import get_app_settings
from app.core.settings.app import AppSettings
from app.db.repositories.users import UsersRepository
from app.models.domain.users import User
from app.models.schemas.users import UserInResponse, UserInUpdate
from app.resources import strings
from app.services.authentication import check_email_is_taken, check_username_is_taken

router = APIRouter()


@router.get("", response_model=UserInResponse, name="users:get-current-user")
async def retrieve_current_user(
    user: User = Depends(get_current_user_authorizer()),
    settings: AppSettings = Depends(get_app_settings),
) -> UserInResponse:
    return build_user_response(user, settings)


@router.put("", response_model=UserInResponse, name="users:update-current-user")
async def update_current_user(
    user_update: UserInUpdate = Body(..., embed=True, alias="user"),
    current_user: User = Depends(get_current_user_authorizer()),
    users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
    settings: AppSettings = Depends(get_app_settings),
) -> UserInResponse:
    if (
        user_update.username
        and user_update.username != current_user.username
        and await check_username_is_taken(users_repo, user_update.username)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=strings.USERNAME_TAKEN,
        )

    if (
        user_update.email
        and user_update.email.lower() != current_user.email
        and await check_email_is_taken(users_repo, user_update.email)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=strings.EMAIL_TAKEN,
        )

    user = await users_repo.update_user(
        user=current_user,
        username=user_update.username,
        email=user_update.email,
        password=user_update.password,
        bio=user_update.bio,
        image=str(user_update.image) if user_update.image else None,
    )
    return build_user_response(user, settings)
