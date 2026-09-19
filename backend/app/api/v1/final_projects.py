from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    SessionDep,
    get_current_active_assignment_manager,
    get_current_active_user,
)
from app.crud.crud_project_submission import (
    project_submission as crud_project_submission,
)
from app.models.final_project import TrainingProject
from app.models.project_submission import ProjectSubmission
from app.models.user import User as UserModel
from app.schemas.project_submission import (
    ProjectReviewCreate,
    ProjectSubmissionCreate,
    ProjectSubmissionResponse,
)

router = APIRouter()

CurrentUserDep = Annotated[
    UserModel,
    Depends(get_current_active_user),
]

CurrentAssignmentManagerDep = Annotated[
    UserModel,
    Depends(get_current_active_assignment_manager),
]


def _get_project_or_404(session: SessionDep, project_id: int) -> TrainingProject:
    project = session.get(TrainingProject, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training project not found",
        )
    return project


def _get_submission_or_404(
    session: SessionDep,
    submission_id: int,
) -> ProjectSubmission:
    submission = crud_project_submission.get(session, id=submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project submission not found",
        )
    return submission


@router.post(
    "/submissions",
    response_model=ProjectSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project_submission(
    session: SessionDep,
    submission_in: ProjectSubmissionCreate,
    current_user: CurrentUserDep,
) -> ProjectSubmission:
    project = _get_project_or_404(session, submission_in.project_id)
    if not project.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training project not found",
        )

    try:
        return crud_project_submission.create_for_user(
            session,
            user_id=current_user.id,
            obj_in=submission_in,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from None


@router.get(
    "/submissions/me",
    response_model=list[ProjectSubmissionResponse],
)
def read_my_project_submissions(
    session: SessionDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
) -> list[ProjectSubmission]:
    submissions = crud_project_submission.get_multi_by_user(
        session,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return list(submissions)


@router.get(
    "/{project_id}/submissions",
    response_model=list[ProjectSubmissionResponse],
)
def read_project_submissions(
    project_id: int,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
    skip: int = 0,
    limit: int = 100,
) -> list[ProjectSubmission]:
    del current_user
    _get_project_or_404(session, project_id)
    submissions = crud_project_submission.get_multi_by_project(
        session,
        project_id=project_id,
        skip=skip,
        limit=limit,
    )
    return list(submissions)


@router.post(
    "/submissions/{submission_id}/review",
    response_model=ProjectSubmissionResponse,
)
def review_project_submission(
    submission_id: int,
    review_in: ProjectReviewCreate,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
) -> ProjectSubmission:
    submission = _get_submission_or_404(session, submission_id)
    return crud_project_submission.review(
        session,
        db_obj=submission,
        reviewer_id=current_user.id,
        obj_in=review_in,
    )
