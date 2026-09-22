from __future__ import annotations

from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.api.deps import (
    SessionDep,
    get_current_active_assignment_manager,
    get_current_active_user,
)
from app.crud.crud_assignment import assignment as crud_assignment
from app.crud.crud_submission import submission as crud_submission
from app.models.submission import Submission, SubmissionFile, SubmissionStatus
from app.models.track_instructor import TrackInstructor
from app.models.user import User as UserModel
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionDetailResponse,
    SubmissionResponse,
    SubmissionReview,
    SubmissionReviewCreate,
    SubmissionUpdate,
)
from app.schemas.submission_file import SubmissionFileResponse
from app.services.storage import StorageService, get_storage_service

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

StorageServiceDep = Annotated[
    StorageService,
    Depends(get_storage_service),
]

UploadFilesDep = Annotated[
    list[UploadFile],
    File(...),
]


def _is_admin_or_superuser(user: UserModel) -> bool:
    if user.is_superuser:
        return True

    role_name = user.role_rel.name.casefold() if user.role_rel else ""
    return role_name == "admin"


def _is_instructor(user: UserModel) -> bool:
    role_name = user.role_rel.name.casefold() if user.role_rel else ""
    return role_name == "instructor"


def _is_instructor_assigned_to_track(
    session: SessionDep,
    *,
    instructor_id: int,
    track_id: int | None,
) -> bool:
    if track_id is None:
        return False

    stmt = select(TrackInstructor.track_id).where(
        TrackInstructor.track_id == track_id,
        TrackInstructor.instructor_id == instructor_id,
    )
    return session.scalar(stmt) is not None


def _can_manage_assignment_submissions(
    session: SessionDep,
    *,
    user: UserModel,
    track_id: int | None,
) -> bool:
    if _is_admin_or_superuser(user):
        return True

    if not _is_instructor(user):
        return False

    return _is_instructor_assigned_to_track(
        session,
        instructor_id=user.id,
        track_id=track_id,
    )


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


def _ensure_submission_manager_access(
    session: SessionDep,
    *,
    user: UserModel,
    submission: Submission,
) -> None:
    if _can_manage_assignment_submissions(
        session,
        user=user,
        track_id=submission.assignment.track_id,
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have access to this submission.",
    )


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


@router.get("/{submission_id}", response_model=SubmissionDetailResponse)
def read_submission(
    submission_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Submission:
    submission = session.scalar(
        select(Submission)
        .options(
            joinedload(Submission.assignment),
            selectinload(Submission.files),
            selectinload(Submission.reviews),
        )
        .where(Submission.id == submission_id)
    )
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    if submission.user_id == current_user.id:
        return submission

    _ensure_submission_manager_access(
        session,
        user=current_user,
        submission=submission,
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
            detail="Only draft or changes-required submissions can be updated.",
        )

    submission_data = (
        submission_in.model_dump(exclude_unset=True)
        if hasattr(submission_in, "model_dump")
        else submission_in
    )
    if submission_in.status == SubmissionStatus.SUBMITTED.value:
        submission_data["status"] = SubmissionStatus.SUBMITTED.value

    return crud_submission.update(
        session,
        db_obj=submission,
        obj_in=submission_data,
    )


@router.post(
    "/{submission_id}/reviews",
    response_model=SubmissionResponse,
)
def create_submission_review(
    submission_id: int,
    review_in: SubmissionReviewCreate,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
) -> Submission:
    submission = _get_submission_or_404(session, submission_id)
    _ensure_submission_manager_access(
        session,
        user=current_user,
        submission=submission,
    )

    if submission.status == SubmissionStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Draft submissions cannot be reviewed.",
        )

    return crud_submission.create_review_and_transition(
        session,
        db_obj=submission,
        reviewer_id=current_user.id,
        obj_in=review_in,
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
    assignment = crud_assignment.get(session, id=assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    if not _can_manage_assignment_submissions(
        session,
        user=current_user,
        track_id=assignment.track_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor is not assigned to this track.",
        )

    submissions = crud_submission.get_multi_by_assignment(
        session,
        assignment_id=assignment_id,
        skip=skip,
        limit=limit,
    )
    return list(submissions)
def _ensure_submission_file_write_access(
    submission: Submission,
    current_user: UserModel,
) -> None:
    if submission.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the submission owner can manage its files.",
        )

    if submission.status not in {
        SubmissionStatus.DRAFT.value,
        SubmissionStatus.CHANGES_REQUIRED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Files can only be changed while the submission is editable.",
        )


def _build_submission_file_key(
    submission_id: int,
    file_name: str | None,
) -> str:
    safe_name = Path(file_name or "unnamed-file").name
    return f"submissions/{submission_id}/{uuid4().hex}_{safe_name}"


@router.post(
    "/{submission_id}/files",
    response_model=list[SubmissionFileResponse],
    status_code=status.HTTP_201_CREATED,
)
def upload_submission_files(
    submission_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
    storage: StorageServiceDep,
    files: UploadFilesDep,
) -> list[SubmissionFile]:
    submission = _get_submission_or_404(session, submission_id)
    _ensure_submission_file_write_access(submission, current_user)

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file is required.",
        )

    stored_keys: list[str] = []
    db_files: list[SubmissionFile] = []

    try:
        for upload in files:
            object_key = _build_submission_file_key(
                submission.id,
                upload.filename,
            )
            stored = storage.upload_file(
                file=upload.file,
                object_key=object_key,
                content_type=upload.content_type,
            )
            stored_keys.append(stored.object_key)

            db_file = SubmissionFile(
                submission_id=submission.id,
                file_name=upload.filename or "unnamed-file",
                file_path=stored.object_key,
                file_size=stored.size_bytes,
                content_type=upload.content_type or "application/octet-stream",
            )
            session.add(db_file)
            db_files.append(db_file)

        session.commit()

        for db_file in db_files:
            session.refresh(db_file)

        return db_files
    except Exception:
        session.rollback()
        for object_key in reversed(stored_keys):
            storage.delete_file(object_key=object_key)
        raise


@router.delete(
    "/{submission_id}/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def delete_submission_file(
    submission_id: int,
    file_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    storage: StorageServiceDep,
) -> None:
    submission = _get_submission_or_404(session, submission_id)
    _ensure_submission_file_write_access(submission, current_user)

    db_file = session.get(SubmissionFile, file_id)
    if not db_file or db_file.submission_id != submission.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission file not found",
        )

    storage.delete_file(object_key=db_file.file_path)
    session.delete(db_file)
    session.commit()

