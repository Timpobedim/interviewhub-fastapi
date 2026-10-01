from fastapi import APIRouter, Body, Depends, HTTPException, Response
from starlette import status

from app.api.dependencies.authentication import get_current_user_authorizer
from app.api.dependencies.database import get_repository
from app.api.dependencies.questions import (
    check_question_modification_permissions,
    get_question_by_slug_from_path,
    get_questions_filters,
)
from app.db.repositories.questions import QuestionsRepository
from app.models.domain.questions import Question
from app.models.domain.users import User
from app.models.schemas.questions import (
    ListOfQuestionsInResponse,
    QuestionForResponse,
    QuestionInCreate,
    QuestionInResponse,
    QuestionInUpdate,
    QuestionsFilters,
)
from app.resources import strings
from app.services.questions import check_question_exists, get_slug_for_question

router = APIRouter()


@router.get("", response_model=ListOfQuestionsInResponse, name="questions:list-questions")
async def list_questions(
    questions_filters: QuestionsFilters = Depends(get_questions_filters),
    user: User | None = Depends(get_current_user_authorizer(required=False)),
    questions_repo: QuestionsRepository = Depends(get_repository(QuestionsRepository)),
) -> ListOfQuestionsInResponse:
    questions, total = await questions_repo.filter_questions(
        tag=questions_filters.tag,
        author=questions_filters.author,
        favorited=questions_filters.favorited,
        grade=questions_filters.grade,
        company=questions_filters.company,
        limit=questions_filters.limit,
        offset=questions_filters.offset,
        requested_user=user,
    )
    return ListOfQuestionsInResponse(
        questions=[QuestionForResponse.model_validate(question) for question in questions],
        questions_count=total,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=QuestionInResponse,
    name="questions:create-question",
)
async def create_new_question(
    question_create: QuestionInCreate = Body(..., embed=True, alias="question"),
    user: User = Depends(get_current_user_authorizer()),
    questions_repo: QuestionsRepository = Depends(get_repository(QuestionsRepository)),
) -> QuestionInResponse:
    slug = get_slug_for_question(question_create.title)
    if await check_question_exists(questions_repo, slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=strings.QUESTION_ALREADY_EXISTS,
        )

    question = await questions_repo.create_question(
        slug=slug,
        title=question_create.title,
        summary=question_create.summary,
        answer=question_create.answer,
        grade=question_create.grade,
        company=question_create.company,
        author=user,
        tags=question_create.tags,
    )
    return QuestionInResponse(question=QuestionForResponse.model_validate(question))


@router.get("/{slug}", response_model=QuestionInResponse, name="questions:get-question")
async def retrieve_question_by_slug(
    question: Question = Depends(get_question_by_slug_from_path),
) -> QuestionInResponse:
    return QuestionInResponse(question=QuestionForResponse.model_validate(question))


@router.put(
    "/{slug}",
    response_model=QuestionInResponse,
    name="questions:update-question",
    dependencies=[Depends(check_question_modification_permissions)],
)
async def update_question_by_slug(
    question_update: QuestionInUpdate = Body(..., embed=True, alias="question"),
    current_question: Question = Depends(get_question_by_slug_from_path),
    questions_repo: QuestionsRepository = Depends(get_repository(QuestionsRepository)),
) -> QuestionInResponse:
    new_slug: str | None = None
    if question_update.title and question_update.title != current_question.title:
        new_slug = get_slug_for_question(question_update.title)
        if new_slug != current_question.slug and await check_question_exists(
            questions_repo,
            new_slug,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=strings.QUESTION_ALREADY_EXISTS,
            )

    question = await questions_repo.update_question(
        question=current_question,
        changes=question_update.model_dump(exclude_unset=True),
        new_slug=new_slug,
    )
    return QuestionInResponse(question=QuestionForResponse.model_validate(question))


@router.delete(
    "/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    name="questions:delete-question",
    dependencies=[Depends(check_question_modification_permissions)],
    response_class=Response,
)
async def delete_question_by_slug(
    question: Question = Depends(get_question_by_slug_from_path),
    questions_repo: QuestionsRepository = Depends(get_repository(QuestionsRepository)),
) -> None:
    await questions_repo.delete_question(question=question)
