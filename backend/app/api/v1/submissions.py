from __future__ import annotations

from contextlib import contextmanager
import logging
from typing import Annotated
from urllib.parse import quote
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from pydantic import PositiveInt
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

from app.api.deps import (
    SessionDep,
    get_current_active_assignment_manager,
    get_current_active_user,
)
from app.crud.crud_submission import SubmissionStateError
from app.core.config import settings
from app.crud.crud_submission import submission as crud_submission
from app.models.submission import Submission, SubmissionFile
from app.models.user import User as UserModel
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionDetailResponse,
    SubmissionResponse,
    SubmissionReviewCreate,
    SubmissionUpdate,
)
from app.schemas.submission_file import SubmissionFileResponse
from app.services.storage import FileTooLargeError, StorageService, get_storage_service

router = APIRouter()
logger = logging.getLogger(__name__)
assignment_submissions_router = APIRouter()
CurrentUserDep = Annotated[UserModel, Depends(get_current_active_user)]
CurrentAssignmentManagerDep = Annotated[
    UserModel, Depends(get_current_active_assignment_manager)
]
StorageServiceDep = Annotated[StorageService, Depends(get_storage_service)]
UploadFilesDep = Annotated[list[UploadFile], File(...)]
Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=0)]


@contextmanager
def _submission_errors():
    try:
        yield
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except SubmissionStateError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def _get_submission(session: SessionDep, submission_id: int) -> Submission:
    submission = crud_submission.get(session, id=submission_id)
    if submission is None:
        raise LookupError("Submission not found")
    return submission


@router.post("", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
def create_submission(
    session: SessionDep, submission_in: SubmissionCreate, current_user: CurrentUserDep
) -> Submission:
    with _submission_errors():
        return crud_submission.create(session, obj_in=submission_in, actor=current_user)


@router.get("/me", response_model=list[SubmissionResponse])
def read_my_submissions(
    session: SessionDep,
    current_user: CurrentUserDep,
    skip: Offset = 0,
    limit: Limit = 100,
    assignment_id: PositiveInt | None = None,
) -> list[Submission]:
    with _submission_errors():
        return list(
            crud_submission.get_multi_by_user(
                session,
                actor=current_user,
                skip=skip,
                limit=limit,
                assignment_id=assignment_id,
            )
        )


@router.get("/{submission_id}", response_model=SubmissionDetailResponse)
def read_submission(
    submission_id: PositiveInt, session: SessionDep, current_user: CurrentUserDep
) -> Submission:
    with _submission_errors():
        return crud_submission.get_for_user(
            session, submission_id=submission_id, actor=current_user
        )


@router.patch("/{submission_id}", response_model=SubmissionResponse)
def update_submission(
    submission_id: PositiveInt,
    session: SessionDep,
    submission_in: SubmissionUpdate,
    current_user: CurrentUserDep,
) -> Submission:
    with _submission_errors():
        return crud_submission.update(
            session,
            db_obj=_get_submission(session, submission_id),
            obj_in=submission_in,
            actor=current_user,
        )


@router.post("/{submission_id}/review", response_model=SubmissionResponse)
def review_submission(
    submission_id: PositiveInt,
    review_in: SubmissionReviewCreate,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
) -> Submission:
    with _submission_errors():
        return crud_submission.create_review_and_transition(
            session,
            db_obj=_get_submission(session, submission_id),
            actor=current_user,
            obj_in=review_in,
        )


@assignment_submissions_router.get(
    "/{assignment_id}/submissions", response_model=list[SubmissionResponse]
)
def read_assignment_submissions(
    assignment_id: PositiveInt,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
    skip: Offset = 0,
    limit: Limit = 100,
) -> list[Submission]:
    with _submission_errors():
        return list(
            crud_submission.get_multi_by_assignment(
                session,
                assignment_id=assignment_id,
                actor=current_user,
                skip=skip,
                limit=limit,
            )
        )


def _file_record(
    session: SessionDep, submission_id: int, file_id: UUID
) -> SubmissionFile:
    record = session.get(SubmissionFile, file_id)
    if record is None or record.submission_id != submission_id:
        raise HTTPException(status_code=404, detail="Submission file not found")
    return record


@router.get("/{submission_id}/files/{file_id}/download")
def download_submission_file(
    submission_id: PositiveInt,
    file_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    storage: StorageServiceDep,
) -> StreamingResponse:
    with _submission_errors():
        crud_submission.get_for_user(
            session, submission_id=submission_id, actor=current_user
        )
    record = _file_record(session, submission_id, file_id)
    try:
        stream = storage.open_file(object_key=record.file_url)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=404, detail="Stored file not found") from error
    except OSError as error:
        raise HTTPException(
            status_code=503, detail="File storage is unavailable"
        ) from error

    def chunks():
        try:
            while data := stream.read(64 * 1024):
                yield data
        finally:
            stream.close()

    return StreamingResponse(
        chunks(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(record.file_name, safe='')}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
        background=BackgroundTask(stream.close),
    )


@router.post(
    "/{submission_id}/files",
    response_model=list[SubmissionFileResponse],
    status_code=status.HTTP_201_CREATED,
)
def upload_submission_files(
    submission_id: PositiveInt,
    session: SessionDep,
    current_user: CurrentUserDep,
    storage: StorageServiceDep,
    files: UploadFilesDep,
) -> list[SubmissionFile]:
    with _submission_errors():
        submission = crud_submission.get_editable(
            session, submission_id=submission_id, actor=current_user
        )
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required.")
    if len(submission.files) + len(files) > settings.SUBMISSION_MAX_FILES:
        raise HTTPException(
            status_code=422,
            detail=f"A submission can contain at most {settings.SUBMISSION_MAX_FILES} files.",
        )
    for upload in files:
        name = upload.filename or "unnamed-file"
        if (
            len(name) > 512
            or any(ord(char) < 32 for char in name)
            or len(upload.content_type or "") > 255
        ):
            raise HTTPException(
                status_code=422, detail="Invalid file name or content type"
            )

    stored_keys: list[str] = []
    db_files: list[SubmissionFile] = []
    try:
        for upload in files:
            object_key = f"submissions/{submission.id}/{uuid4().hex}"
            stored = storage.upload_file(
                file=upload.file,
                object_key=object_key,
                content_type=upload.content_type,
            )
            stored_keys.append(stored.object_key)
            db_file = SubmissionFile(
                submission_id=submission.id,
                file_name=upload.filename or "unnamed-file",
                file_url=stored.object_key,
                file_size=stored.size_bytes,
                file_type=upload.content_type or "application/octet-stream",
            )
            session.add(db_file)
            db_files.append(db_file)
        session.commit()
    except Exception as error:
        session.rollback()
        for object_key in reversed(stored_keys):
            try:
                storage.delete_file(object_key=object_key)
            except OSError:
                logger.exception("Failed to clean up an uncommitted upload")
        if isinstance(error, FileTooLargeError):
            raise HTTPException(status_code=413, detail=str(error)) from error
        if isinstance(error, OSError):
            raise HTTPException(
                status_code=503, detail="File storage is unavailable"
            ) from error
        raise
    # A response/refresh failure must never delete successfully committed files.
    for db_file in db_files:
        session.refresh(db_file)
    return db_files


@router.delete(
    "/{submission_id}/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def delete_submission_file(
    submission_id: PositiveInt,
    file_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    storage: StorageServiceDep,
) -> None:
    with _submission_errors():
        submission = crud_submission.get_editable(
            session, submission_id=submission_id, actor=current_user
        )
    db_file = _file_record(session, submission.id, file_id)
    object_key = db_file.file_url
    session.delete(db_file)
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    # Remove access first. Failed storage cleanup leaves a private orphan, never
    # a database record pointing at bytes lost after a failed database commit.
    try:
        storage.delete_file(object_key=object_key)
    except OSError:
        logger.exception("Failed to remove detached submission file %s", file_id)
