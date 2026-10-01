from fastapi import APIRouter

from app.api.routes import authentication, comments, health, profiles, tags, users
from app.api.routes.questions import api as questions

router = APIRouter()
router.include_router(health.router, tags=["health"], prefix="/health")
router.include_router(authentication.router, tags=["authentication"], prefix="/users")
router.include_router(users.router, tags=["users"], prefix="/user")
router.include_router(profiles.router, tags=["profiles"], prefix="/profiles")
router.include_router(questions.router, tags=["questions"])
router.include_router(
    comments.router,
    tags=["comments"],
    prefix="/questions/{slug}/comments",
)
router.include_router(tags.router, tags=["tags"], prefix="/tags")
