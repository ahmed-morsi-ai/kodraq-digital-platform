from __future__ import annotations

from contextlib import contextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import PositiveInt

from app.api.deps import SessionDep, get_current_active_assignment_manager
from app.crud.crud_quiz import question as crud_question
from app.models.quiz import Question
from app.models.user import User as UserModel
from app.schemas.quiz import QuestionCreate, QuestionResponse

router = APIRouter()
track_router = APIRouter()
CurrentAssignmentManagerDep = Annotated[
    UserModel, Depends(get_current_active_assignment_manager)
]


@contextmanager
def _question_errors():
    try:
        yield
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@track_router.post(
    "/{track_id}/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_track_question(
    track_id: PositiveInt,
    question_in: QuestionCreate,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
) -> Question:
    with _question_errors():
        data = question_in.model_dump() | {"track_id": track_id}
        return crud_question.create(
            session, obj_in=QuestionCreate.model_validate(data), actor=current_user
        )


@track_router.get("/{track_id}/questions", response_model=list[QuestionResponse])
def list_track_questions(
    track_id: PositiveInt,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=0)] = 100,
) -> list[Question]:
    with _question_errors():
        return list(
            crud_question.get_multi_by_track(
                session, track_id=track_id, actor=current_user, skip=skip, limit=limit
            )
        )


@router.get("/{question_id}", response_model=QuestionResponse)
def read_question(
    question_id: PositiveInt,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
) -> Question:
    with _question_errors():
        return crud_question.get_for_manager(
            session, id=question_id, actor=current_user
        )


@router.delete(
    "/{question_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
def remove_question(
    question_id: PositiveInt,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
) -> None:
    with _question_errors():
        crud_question.remove(session, id=question_id, actor=current_user)
