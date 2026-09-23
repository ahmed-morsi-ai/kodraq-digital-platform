from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import (
    SessionDep,
    get_current_active_assignment_manager,
)
from app.crud.crud_quiz import (
    create_question,
    delete_question,
    get_question,
    get_questions_by_track,
)
from app.crud.crud_track import track as crud_track
from app.models.quiz import Question
from app.models.track_instructor import TrackInstructor
from app.models.user import User as UserModel
from app.schemas.quiz import QuestionCreate, QuestionResponse

router = APIRouter()
track_router = APIRouter()

CurrentAssignmentManagerDep = Annotated[
    UserModel,
    Depends(get_current_active_assignment_manager),
]


def _is_admin_or_superuser(user: UserModel) -> bool:
    if user.is_superuser:
        return True

    role_name = user.role_rel.name.casefold() if user.role_rel else ""
    return role_name == "admin"


def _ensure_track_access(
    session: SessionDep,
    *,
    track_id: int,
    current_user: UserModel,
) -> None:
    if _is_admin_or_superuser(current_user):
        return

    assigned = session.scalar(
        select(TrackInstructor.track_id).where(
            TrackInstructor.track_id == track_id,
            TrackInstructor.instructor_id == current_user.id,
        )
    )
    if assigned is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor is not assigned to this track.",
        )


def _get_question_or_404(session: SessionDep, question_id: int) -> Question:
    question = get_question(session, question_id)
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )
    return question


@track_router.post(
    "/{track_id}/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_track_question(
    track_id: int,
    question_in: QuestionCreate,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
) -> Question:
    if crud_track.get(session, id=track_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found",
        )

    _ensure_track_access(
        session,
        track_id=track_id,
        current_user=current_user,
    )
    question_data = question_in.model_dump()
    question_data["track_id"] = track_id
    return create_question(
        session,
        QuestionCreate.model_validate(question_data),
    )


@track_router.get(
    "/{track_id}/questions",
    response_model=list[QuestionResponse],
)
def list_track_questions(
    track_id: int,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
    skip: int = 0,
    limit: int = 100,
) -> list[Question]:
    if crud_track.get(session, id=track_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found",
        )

    _ensure_track_access(
        session,
        track_id=track_id,
        current_user=current_user,
    )
    return list(
        get_questions_by_track(
            session,
            track_id=track_id,
            skip=skip,
            limit=limit,
        )
    )


@router.get("/{question_id}", response_model=QuestionResponse)
def read_question(
    question_id: int,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
) -> Question:
    question = _get_question_or_404(session, question_id)
    if question.track_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Question is not assigned to a track.",
        )

    _ensure_track_access(
        session,
        track_id=question.track_id,
        current_user=current_user,
    )
    return question


@router.delete(
    "/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def remove_question(
    question_id: int,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
) -> None:
    question = _get_question_or_404(session, question_id)
    if question.track_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Question is not assigned to a track.",
        )

    _ensure_track_access(
        session,
        track_id=question.track_id,
        current_user=current_user,
    )
    delete_question(session, question_id)
