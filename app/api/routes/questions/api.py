from fastapi import APIRouter

from app.api.routes.questions import questions_common, questions_resource

router = APIRouter()

# Порядок важен: «/questions/feed» должен быть зарегистрирован раньше, чем «/questions/{slug}».
router.include_router(questions_common.router, prefix="/questions")
router.include_router(questions_resource.router, prefix="/questions")
