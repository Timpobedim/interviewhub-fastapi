import secrets

from slugify import slugify

from app.db.errors import EntityDoesNotExistError
from app.db.repositories.questions import QuestionsRepository
from app.models.domain.questions import Question
from app.models.domain.users import User

SLUG_MAX_LENGTH = 120


async def check_question_exists(questions_repo: QuestionsRepository, slug: str) -> bool:
    try:
        await questions_repo.get_question_by_slug(slug=slug)
    except EntityDoesNotExistError:
        return False

    return True


def get_slug_for_question(title: str) -> str:
    """Транслитерирует заголовок в slug: «Что такое GIL в CPython?» → «chto-takoe-gil-v-cpython».

    Если в заголовке нет ни одного пригодного символа, генерируется случайный slug.
    """
    slug = slugify(title, max_length=SLUG_MAX_LENGTH, word_boundary=True)
    return slug or f"question-{secrets.token_hex(4)}"


def check_user_can_modify_question(question: Question, user: User) -> bool:
    return question.author.username == user.username
