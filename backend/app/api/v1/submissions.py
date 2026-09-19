from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    SessionDep,
    get_current_active_assignment_manager,
    get_current_active_user,
)
from app.crud.crud_assignment import assignment as crud_assignment
from app.crud.crud_submission import submission as crud_submission
from app.models.submission import Submission, SubmissionStatus
from app.models.user import User as UserModel
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionResponse,
    SubmissionReview,
    SubmissionUpdate,
)

router = APIRouter()
assignment_submissions_router = APIRouter()

CurrentUserDep = Annotated[
    UserModel,
    Depends(get_current_active_user),
]

CurrentAssignmentManagerDep = Annotated[
    UserModel,
    Depends(get_current_active_assignment_manager),
]


def _is_assignment_manager(user: UserModel) -> bool:
    if user.is_superuser:
        return True

    role_name = user.role_rel.name.casefold() if user.role_rel else ""
    return role_name in {"admin", "instructor"}


def _get_submission_or_404(
    session: SessionDep,
    submission_id: int,
) -> Submission:
    submission = crud_submission.get(session, id=submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    return submission


@router.post(
    "",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_submission(
    session: SessionDep,
    submission_in: SubmissionCreate,
    current_user: CurrentUserDep,
) -> Submission:
    assignment = crud_assignment.get(session, id=submission_in.assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    return crud_submission.create_for_user(
        session,
        user_id=current_user.id,
        obj_in=submission_in,
    )


@router.get("/me", response_model=list[SubmissionResponse])
def read_my_submissions(
    session: SessionDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
) -> list[Submission]:
    submissions = crud_submission.get_multi_by_user(
        session,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return list(submissions)


@router.get("/{submission_id}", response_model=SubmissionResponse)
def read_submission(
    submission_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Submission:
    submission = _get_submission_or_404(session, submission_id)
    if submission.user_id != current_user.id and not _is_assignment_manager(
        current_user
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this submission.",
        )

    return submission


@router.patch("/{submission_id}", response_model=SubmissionResponse)
def update_submission(
    submission_id: int,
    session: SessionDep,
    submission_in: SubmissionUpdate,
    current_user: CurrentUserDep,
) -> Submission:
    submission = _get_submission_or_404(session, submission_id)
    if submission.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the submission owner can update it.",
        )

    if submission.status not in {
        SubmissionStatus.DRAFT.value,
        SubmissionStatus.CHANGES_REQUIRED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only draft submissions can be updated.",
        )

    return crud_submission.update(
        session,
        db_obj=submission,
        obj_in=submission_in,
    )


@router.post(
    "/{submission_id}/review",
    response_model=SubmissionResponse,
)
def review_submission(
    submission_id: int,
    review_in: SubmissionReview,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
) -> Submission:
    del current_user
    submission = _get_submission_or_404(session, submission_id)

    return crud_submission.review(
        session,
        db_obj=submission,
        obj_in=review_in,
    )


@assignment_submissions_router.get(
    "/{assignment_id}/submissions",
    response_model=list[SubmissionResponse],
)
def read_assignment_submissions(
    assignment_id: int,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
    skip: int = 0,
    limit: int = 100,
) -> list[Submission]:
    del current_user

    assignment = crud_assignment.get(session, id=assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    submissions = crud_submission.get_multi_by_assignment(
        session,
        assignment_id=assignment_id,
        skip=skip,
        limit=limit,
    )
    return list(submissions)
