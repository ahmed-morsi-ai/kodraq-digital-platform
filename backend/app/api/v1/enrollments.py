from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.api.deps import (
    SessionDep,
    get_current_active_superuser,
    get_current_active_user,
)
from app.crud.crud_enrollment import (
    enrollment as crud_enrollment,
)
from app.crud.crud_enrollment import (
    student_progress as crud_student_progress,
)
from app.crud.crud_track import track as crud_track
from app.models.enrollment import Enrollment
from app.models.payment import Payment
from app.models.track import Lesson, Track
from app.models.user import User as UserModel
from app.schemas.enrollment import (
    EnrollmentCreate,
    EnrollmentDetail,
    EnrollmentUpdate,
    StudentProgress,
    StudentProgressCreate,
    StudentProgressDetail,
    StudentProgressUpdate,
)

router = APIRouter()

CurrentUserDep = Annotated[
    UserModel,
    Depends(get_current_active_user),
]

CurrentSuperuserDep = Annotated[
    UserModel,
    Depends(get_current_active_superuser),
]


def _require_enrollment_access(
    enrollment: Enrollment,
    current_user: UserModel,
) -> None:
    if not current_user.is_superuser and enrollment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this enrollment.",
        )


@router.post(
    "",
    response_model=EnrollmentDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_enrollment(
    session: SessionDep,
    enrollment_in: EnrollmentCreate,
    current_user: CurrentUserDep,
) -> Enrollment:
    track = session.get(Track, enrollment_in.track_id)
    if track is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found.",
        )

    target_status = "pending_payment" if track.is_premium else "active"
    enrollment_payload = enrollment_in.model_copy(
        update={"status": target_status},
    )
    track = crud_track.get(
        session,
        id=enrollment_payload.track_id,
    )

    if not track or not track.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active track not found",
        )

    existing = crud_enrollment.get_by_user_and_track(
        session,
        user_id=current_user.id,
        track_id=enrollment_payload.track_id,
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already enrolled in this track.",
        )

    try:
        created = crud_enrollment.create_for_user(
            session,
            user_id=current_user.id,
            obj_in=enrollment_payload,
        )
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enrollment could not be created.",
        ) from None

    detail = crud_enrollment.get_detail(
        session,
        id=created.id,
    )

    if not detail:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Enrollment was created but could not be loaded.",
        )

    return detail


@router.get("/me", response_model=list[EnrollmentDetail])
def read_my_enrollments(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[Enrollment]:
    enrollments = crud_enrollment.get_multi_by_user(
        session,
        user_id=current_user.id,
    )

    return [
        detail
        for enrollment_item in enrollments
        if (
            detail := crud_enrollment.get_detail(
                session,
                id=enrollment_item.id,
            )
        )
    ]


@router.get(
    "/track/{track_id}",
    response_model=list[EnrollmentDetail],
)
def read_track_enrollments(
    track_id: int,
    session: SessionDep,
    current_user: CurrentSuperuserDep,
) -> list[Enrollment]:
    del current_user

    track = crud_track.get(
        session,
        id=track_id,
    )

    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found",
        )

    enrollments = crud_enrollment.get_multi_by_track(
        session,
        track_id=track_id,
    )

    return [
        detail
        for enrollment_item in enrollments
        if (
            detail := crud_enrollment.get_detail(
                session,
                id=enrollment_item.id,
            )
        )
    ]


@router.get(
    "/{enrollment_id}",
    response_model=EnrollmentDetail,
)
def read_enrollment(
    enrollment_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Enrollment:
    enrollment = crud_enrollment.get_detail(
        session,
        id=enrollment_id,
    )

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )

    _require_enrollment_access(
        enrollment,
        current_user,
    )

    return enrollment


@router.patch(
    "/{enrollment_id}",
    response_model=EnrollmentDetail,
)
def update_enrollment(
    enrollment_id: int,
    session: SessionDep,
    enrollment_in: EnrollmentUpdate,
    current_user: CurrentSuperuserDep,
) -> Enrollment:
    del current_user

    enrollment = crud_enrollment.get(
        session,
        id=enrollment_id,
    )

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )

    if enrollment_in.status == "active":
        track = crud_track.get(session, id=enrollment.track_id)
        if track and track.is_premium:
            verified_payment = session.execute(
                select(Payment.id)
                .where(
                    Payment.user_id == enrollment.user_id,
                    Payment.track_id == enrollment.track_id,
                    Payment.status == "VERIFIED",
                )
                .limit(1)
            ).scalar_one_or_none()

            if verified_payment is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Premium enrollment cannot be activated until "
                        "a related payment is verified."
                    ),
                )

    updated = crud_enrollment.update(
        session,
        db_obj=enrollment,
        obj_in=enrollment_in,
    )

    detail = crud_enrollment.get_detail(
        session,
        id=updated.id,
    )

    if not detail:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Enrollment was updated but could not be loaded.",
        )

    return detail


@router.get(
    "/{enrollment_id}/progress",
    response_model=list[StudentProgressDetail],
)
def read_enrollment_progress(
    enrollment_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[StudentProgress]:
    enrollment = crud_enrollment.get(
        session,
        id=enrollment_id,
    )

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )

    _require_enrollment_access(
        enrollment,
        current_user,
    )

    return list(
        crud_student_progress.get_multi_by_enrollment(
            session,
            enrollment_id=enrollment_id,
        )
    )


@router.post(
    "/{enrollment_id}/progress",
    response_model=StudentProgressDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_progress(
    enrollment_id: int,
    session: SessionDep,
    progress_in: StudentProgressCreate,
    current_user: CurrentUserDep,
) -> StudentProgress:
    enrollment = crud_enrollment.get(
        session,
        id=enrollment_id,
    )

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )

    _require_enrollment_access(
        enrollment,
        current_user,
    )

    if progress_in.enrollment_id != enrollment_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="enrollment_id does not match the URL enrollment_id.",
        )

    lesson = session.execute(
        select(Lesson)
        .options(joinedload(Lesson.module))
        .where(Lesson.id == progress_in.lesson_id)
    ).scalar_one_or_none()

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    if lesson.module.track_id != enrollment.track_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lesson does not belong to the enrolled track.",
        )

    existing = crud_student_progress.get_by_enrollment_and_lesson(
        session,
        enrollment_id=enrollment_id,
        lesson_id=progress_in.lesson_id,
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Progress for this lesson already exists.",
        )

    created = crud_student_progress.create(
        session,
        obj_in=progress_in,
    )

    detail = crud_student_progress.get_detail(
        session,
        id=created.id,
    )

    if not detail:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Progress was created but could not be loaded.",
        )

    return detail


@router.patch(
    "/{enrollment_id}/progress/{progress_id}",
    response_model=StudentProgressDetail,
)
def update_progress(
    enrollment_id: int,
    progress_id: int,
    session: SessionDep,
    progress_in: StudentProgressUpdate,
    current_user: CurrentUserDep,
) -> StudentProgress:
    enrollment = crud_enrollment.get(
        session,
        id=enrollment_id,
    )

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )

    _require_enrollment_access(
        enrollment,
        current_user,
    )

    progress = crud_student_progress.get_detail(
        session,
        id=progress_id,
    )

    if not progress or progress.enrollment_id != enrollment_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Progress record not found",
        )

    updated = crud_student_progress.update(
        session,
        db_obj=progress,
        obj_in=progress_in,
    )

    detail = crud_student_progress.get_detail(
        session,
        id=updated.id,
    )

    if not detail:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Progress was updated but could not be loaded.",
        )

    return detail
