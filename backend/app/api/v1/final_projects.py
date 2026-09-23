from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import (
    SessionDep,
    get_current_active_assignment_manager,
    get_current_active_user,
)
from app.crud.crud_final_project import (
    training_project as crud_training_project,
)
from app.crud.crud_project_submission import (
    project_submission as crud_project_submission,
)
from app.crud.crud_track import track as crud_track
from app.models.enrollment import Enrollment
from app.models.final_project import ProjectReview, TrainingProject
from app.models.project_submission import (
    ProjectSubmission,
    ProjectSubmissionStatus,
)
from app.models.track_instructor import TrackInstructor
from app.models.user import User as UserModel
from app.schemas.final_project import (
    ProjectReviewCreate as FinalProjectReviewCreate,
)
from app.schemas.final_project import (
    ProjectReviewResponse,
    ProjectSubmissionCreate,
    ProjectSubmissionResponse,
    ProjectSubmissionUpdate,
    TrainingProjectCreate,
    TrainingProjectResponse,
    TrainingProjectUpdate,
)
from app.schemas.project_submission import (
    ProjectReviewCreate,
)
from app.schemas.project_submission import (
    ProjectSubmissionCreate as LegacyProjectSubmissionCreate,
)
from app.schemas.project_submission import (
    ProjectSubmissionResponse as LegacyProjectSubmissionResponse,
)

router = APIRouter()
track_router = APIRouter()

CurrentUserDep = Annotated[
    UserModel,
    Depends(get_current_active_user),
]

CurrentAssignmentManagerDep = Annotated[
    UserModel,
    Depends(get_current_active_assignment_manager),
]


def _is_admin_or_superuser(user: UserModel) -> bool:
    if user.is_superuser:
        return True

    role_name = user.role_rel.name.casefold() if user.role_rel else ""
    return role_name == "admin"


def _ensure_track_write_access(
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


def _ensure_track_read_access(
    session: SessionDep,
    *,
    track_id: int,
    current_user: UserModel,
) -> None:
    if _is_admin_or_superuser(current_user):
        return

    role_name = current_user.role_rel.name.casefold() if current_user.role_rel else ""

    if role_name == "instructor":
        _ensure_track_write_access(
            session,
            track_id=track_id,
            current_user=current_user,
        )
        return

    enrolled = session.scalar(
        select(Enrollment.id).where(
            Enrollment.user_id == current_user.id,
            Enrollment.track_id == track_id,
            Enrollment.status == "active",
        )
    )

    if enrolled is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be actively enrolled in this track.",
        )


def _get_project_or_404(
    session: SessionDep,
    project_id: int,
) -> TrainingProject:
    project = crud_training_project.get(
        session,
        project_id=project_id,
    )
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training project not found",
        )
    return project


def _get_submission_or_404(
    session: SessionDep,
    submission_id: int,
) -> ProjectSubmission:
    submission = crud_project_submission.get(
        session,
        id=submission_id,
    )
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project submission not found",
        )
    return submission


def _ensure_active_enrollment(
    session: SessionDep,
    *,
    user_id: int,
    track_id: int,
) -> None:
    enrolled = session.scalar(
        select(Enrollment.id).where(
            Enrollment.user_id == user_id,
            Enrollment.track_id == track_id,
            Enrollment.status == "active",
        )
    )
    if enrolled is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be actively enrolled in this track.",
        )


@track_router.post(
    "/{track_id}/final-project",
    response_model=TrainingProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_final_project(
    track_id: int,
    project_in: TrainingProjectCreate,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
) -> TrainingProject:
    if crud_track.get(session, id=track_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found",
        )

    _ensure_track_write_access(
        session,
        track_id=track_id,
        current_user=current_user,
    )

    if crud_training_project.get_by_track(
        session,
        track_id=track_id,
    ) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A final project already exists for this track.",
        )

    try:
        return crud_training_project.create(
            session,
            track_id=track_id,
            obj_in=project_in,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from None


@track_router.get(
    "/{track_id}/final-project",
    response_model=TrainingProjectResponse,
)
def read_track_final_project(
    track_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TrainingProject:
    if crud_track.get(session, id=track_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found",
        )

    _ensure_track_read_access(
        session,
        track_id=track_id,
        current_user=current_user,
    )

    project = crud_training_project.get_by_track(
        session,
        track_id=track_id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Final project not found",
        )

    return project


@router.patch(
    "/{project_id}",
    response_model=TrainingProjectResponse,
)
def update_final_project(
    project_id: int,
    project_in: TrainingProjectUpdate,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
) -> TrainingProject:
    project = _get_project_or_404(session, project_id)

    _ensure_track_write_access(
        session,
        track_id=project.track_id,
        current_user=current_user,
    )

    return crud_training_project.update(
        session,
        db_obj=project,
        obj_in=project_in,
    )


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_final_project(
    project_id: int,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
) -> None:
    project = _get_project_or_404(session, project_id)

    _ensure_track_write_access(
        session,
        track_id=project.track_id,
        current_user=current_user,
    )

    crud_training_project.remove(
        session,
        db_obj=project,
    )


# ------------------------------------------------------------
# TASK-5.4.3: Project submissions
# ------------------------------------------------------------

@router.post(
    "/submissions",
    response_model=ProjectSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_legacy_project_submission(
    session: SessionDep,
    submission_in: LegacyProjectSubmissionCreate,
    current_user: CurrentUserDep,
) -> ProjectSubmission:
    project = _get_project_or_404(
        session,
        submission_in.project_id,
    )

    if not project.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training project not found",
        )

    _ensure_active_enrollment(
        session,
        user_id=current_user.id,
        track_id=project.track_id,
    )

    new_submission = ProjectSubmissionCreate(
        github_url=submission_in.repository_url,
        live_url=submission_in.live_url,
        file_url=submission_in.documentation_url,
    )

    try:
        return crud_project_submission.create_for_user(
            session,
            user_id=current_user.id,
            project_id=project.id,
            obj_in=new_submission,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from None

@router.post(
    "/{project_id}/submissions",
    response_model=ProjectSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project_submission(
    project_id: int,
    submission_in: ProjectSubmissionCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ProjectSubmission:
    project = _get_project_or_404(session, project_id)

    if not project.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training project not found",
        )

    _ensure_active_enrollment(
        session,
        user_id=current_user.id,
        track_id=project.track_id,
    )

    try:
        return crud_project_submission.create_for_user(
            session,
            user_id=current_user.id,
            project_id=project_id,
            obj_in=submission_in,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
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
    project = _get_project_or_404(session, project_id)

    _ensure_track_write_access(
        session,
        track_id=project.track_id,
        current_user=current_user,
    )

    submissions = crud_project_submission.get_multi_by_project(
        session,
        project_id=project_id,
        skip=skip,
        limit=limit,
    )
    return list(submissions)


@router.patch(
    "/submissions/{submission_id}",
    response_model=ProjectSubmissionResponse,
)
def update_project_submission(
    submission_id: int,
    submission_in: ProjectSubmissionUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ProjectSubmission:
    submission = _get_submission_or_404(
        session,
        submission_id,
    )

    if submission.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the submission owner can update it.",
        )

    if submission.status not in {
        ProjectSubmissionStatus.DRAFT.value,
        ProjectSubmissionStatus.CHANGES_REQUIRED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only draft or changes-required submissions can be updated."
            ),
        )

    return crud_project_submission.update(
        session,
        db_obj=submission,
        obj_in=submission_in,
    )


@router.post(
    "/submissions/{submission_id}/reviews",
    response_model=ProjectReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project_review(
    submission_id: int,
    review_in: FinalProjectReviewCreate,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
) -> ProjectReview:
    submission = _get_submission_or_404(
        session,
        submission_id,
    )

    _ensure_track_write_access(
        session,
        track_id=submission.project.track_id,
        current_user=current_user,
    )

    try:
        return crud_project_submission.create_review(
            session,
            db_obj=submission,
            reviewer_id=current_user.id,
            obj_in=review_in,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from None


@router.get(
    "/submissions/{submission_id}/reviews",
    response_model=list[ProjectReviewResponse],
)
def read_project_reviews(
    submission_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[ProjectReview]:
    submission = _get_submission_or_404(
        session,
        submission_id,
    )

    if _is_admin_or_superuser(current_user):
        pass
    else:
        role_name = (
            current_user.role_rel.name.casefold()
            if current_user.role_rel
            else ""
        )

        if role_name == "instructor":
            _ensure_track_write_access(
                session,
                track_id=submission.project.track_id,
                current_user=current_user,
            )
        elif submission.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view reviews for your own submission.",
            )

    reviews = crud_project_submission.get_reviews(
        session,
        submission_id=submission_id,
    )
    return list(reviews)


@router.post(
    "/submissions/{submission_id}/review",
    response_model=LegacyProjectSubmissionResponse,
)
def review_project_submission(
    submission_id: int,
    review_in: ProjectReviewCreate,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
) -> ProjectSubmission:
    submission = _get_submission_or_404(
        session,
        submission_id,
    )

    return crud_project_submission.review(
        session,
        db_obj=submission,
        reviewer_id=current_user.id,
        obj_in=review_in,
    )
