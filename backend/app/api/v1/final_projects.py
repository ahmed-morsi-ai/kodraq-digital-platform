from contextlib import contextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import PositiveInt

from app.api.deps import SessionDep, get_current_active_user
from app.crud.crud_final_project import training_project as projects
from app.crud.crud_project_submission import project_submission as submissions
from app.models.user import User
from app.schemas.final_project import (
    ProjectReviewCreate,
    ProjectReviewResponse,
    ProjectSubmissionCreate,
    ProjectSubmissionResponse,
    ProjectSubmissionUpdate,
    TrainingProjectCreate,
    TrainingProjectResponse,
    TrainingProjectUpdate,
)
from app.services.final_project_access import ProjectConflictError

router = APIRouter()
track_router = APIRouter()
CurrentUser = Annotated[User, Depends(get_current_active_user)]
Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]


@contextmanager
def _http_errors():
    try:
        yield
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ProjectConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@track_router.post(
    "/{track_id}/final-project", response_model=TrainingProjectResponse, status_code=201
)
def create_final_project(
    track_id: PositiveInt,
    project_in: TrainingProjectCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    with _http_errors():
        return projects.create(
            session, track_id=track_id, obj_in=project_in, actor=current_user
        )


@track_router.get("/{track_id}/final-project", response_model=TrainingProjectResponse)
def read_track_final_project(
    track_id: PositiveInt, session: SessionDep, current_user: CurrentUser
):
    with _http_errors():
        return projects.get_by_track(session, track_id=track_id, actor=current_user)


@router.get("/submissions/me", response_model=list[ProjectSubmissionResponse])
def read_my_project_submissions(
    session: SessionDep,
    current_user: CurrentUser,
    project_id: PositiveInt | None = None,
    skip: Offset = 0,
    limit: Limit = 100,
):
    with _http_errors():
        return submissions.get_mine(
            session, actor=current_user, project_id=project_id, skip=skip, limit=limit
        )


@router.get("/submissions/{submission_id}", response_model=ProjectSubmissionResponse)
def read_project_submission(
    submission_id: PositiveInt, session: SessionDep, current_user: CurrentUser
):
    with _http_errors():
        return submissions.get(session, submission_id, actor=current_user)


@router.patch("/submissions/{submission_id}", response_model=ProjectSubmissionResponse)
def update_project_submission(
    submission_id: PositiveInt,
    submission_in: ProjectSubmissionUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    with _http_errors():
        return submissions.update(
            session,
            submission_id=submission_id,
            obj_in=submission_in,
            actor=current_user,
        )


@router.post(
    "/submissions/{submission_id}/reviews",
    response_model=ProjectReviewResponse,
    status_code=201,
)
def create_project_review(
    submission_id: PositiveInt,
    review_in: ProjectReviewCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    with _http_errors():
        return submissions.create_review(
            session, submission_id=submission_id, obj_in=review_in, actor=current_user
        )


@router.get(
    "/submissions/{submission_id}/reviews", response_model=list[ProjectReviewResponse]
)
def read_project_reviews(
    submission_id: PositiveInt, session: SessionDep, current_user: CurrentUser
):
    with _http_errors():
        return submissions.get_reviews(
            session, submission_id=submission_id, actor=current_user
        )


@router.get("/{project_id}", response_model=TrainingProjectResponse)
def read_final_project(
    project_id: PositiveInt, session: SessionDep, current_user: CurrentUser
):
    with _http_errors():
        return projects.get(session, project_id=project_id, actor=current_user)


@router.patch("/{project_id}", response_model=TrainingProjectResponse)
def update_final_project(
    project_id: PositiveInt,
    project_in: TrainingProjectUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    with _http_errors():
        return projects.update(
            session, project_id=project_id, obj_in=project_in, actor=current_user
        )


@router.delete("/{project_id}", status_code=204, response_model=None)
def delete_final_project(
    project_id: PositiveInt, session: SessionDep, current_user: CurrentUser
):
    with _http_errors():
        projects.remove(session, project_id=project_id, actor=current_user)


@router.post(
    "/{project_id}/submissions",
    response_model=ProjectSubmissionResponse,
    status_code=201,
)
def create_project_submission(
    project_id: PositiveInt,
    submission_in: ProjectSubmissionCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    with _http_errors():
        return submissions.create(
            session, project_id=project_id, obj_in=submission_in, actor=current_user
        )


@router.get("/{project_id}/submissions", response_model=list[ProjectSubmissionResponse])
def read_project_submissions(
    project_id: PositiveInt,
    session: SessionDep,
    current_user: CurrentUser,
    skip: Offset = 0,
    limit: Limit = 100,
):
    with _http_errors():
        return submissions.get_multi_by_project(
            session, project_id=project_id, actor=current_user, skip=skip, limit=limit
        )
