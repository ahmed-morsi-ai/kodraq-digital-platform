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
from app.models.enrollment import Enrollment, StudentProgress as StudentProgressModel
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
from app.schemas.track import CurriculumLesson, LessonQuizPrompt

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


def _progress_response(
    progress: StudentProgressModel,
    enrollment: Enrollment,
    current_user: UserModel,
) -> StudentProgressDetail:
    lesson = progress.lesson
    lesson_payload = None
    if lesson is not None:
        entitled = current_user.is_superuser or (
            enrollment.user_id == current_user.id and enrollment.status == "active"
        )
        lesson_payload = CurriculumLesson(
            id=lesson.id,
            module_id=lesson.module_id,
            title=lesson.title,
            description=lesson.description,
            ordering=lesson.ordering,
            **(
                {
                    "content": lesson.content,
                    "video_url": lesson.video_url,
                    "quiz_data": (
                        [
                            LessonQuizPrompt.model_validate(question)
                            for question in lesson.quiz_data
                        ]
                        if lesson.quiz_data is not None
                        else None
                    ),
                }
                if entitled
                else {}
            ),
        )
    progress_payload = StudentProgress.model_validate(progress, from_attributes=True)
    return StudentProgressDetail(
        **progress_payload.model_dump(),
        lesson=lesson_payload,
    )


def _enrollment_response(
    enrollment: Enrollment,
    current_user: UserModel,
) -> EnrollmentDetail:
    return EnrollmentDetail(
        id=enrollment.id,
        user_id=enrollment.user_id,
        track_id=enrollment.track_id,
        status=enrollment.status,
        enrolled_at=enrollment.enrolled_at,
        completed_at=enrollment.completed_at,
        track=enrollment.track,
        progress=[
            _progress_response(progress, enrollment, current_user)
            for progress in enrollment.progress
        ],
    )


@router.post(
    "",
    response_model=EnrollmentDetail,
    response_model_exclude_unset=True,
    status_code=status.HTTP_201_CREATED,
)
def create_enrollment(
    session: SessionDep,
    enrollment_in: EnrollmentCreate,
    current_user: CurrentUserDep,
) -> EnrollmentDetail:
    track = session.get(Track, enrollment_in.track_id)
    if track is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found.",
        )

    enrollment_payload = enrollment_in.model_copy(
        update={"status": "pending"},
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

    return _enrollment_response(detail, current_user)


@router.get(
    "/me",
    response_model=list[EnrollmentDetail],
    response_model_exclude_unset=True,
)
def read_my_enrollments(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[EnrollmentDetail]:
    enrollments = crud_enrollment.get_multi_by_user(
        session,
        user_id=current_user.id,
    )

    return [
        _enrollment_response(detail, current_user)
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
    response_model_exclude_unset=True,
)
def read_track_enrollments(
    track_id: int,
    session: SessionDep,
    current_user: CurrentSuperuserDep,
) -> list[EnrollmentDetail]:
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
        _enrollment_response(detail, current_user)
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
    response_model_exclude_unset=True,
)
def read_enrollment(
    enrollment_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> EnrollmentDetail:
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

    return _enrollment_response(enrollment, current_user)


@router.patch(
    "/{enrollment_id}",
    response_model=EnrollmentDetail,
    response_model_exclude_unset=True,
)
def update_enrollment(
    enrollment_id: int,
    session: SessionDep,
    enrollment_in: EnrollmentUpdate,
    current_user: CurrentSuperuserDep,
) -> EnrollmentDetail:
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

    return _enrollment_response(detail, current_user)


@router.get(
    "/{enrollment_id}/progress",
    response_model=list[StudentProgressDetail],
    response_model_exclude_unset=True,
)
def read_enrollment_progress(
    enrollment_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[StudentProgressDetail]:
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

    return [
        _progress_response(progress, enrollment, current_user)
        for progress in crud_student_progress.get_multi_by_enrollment(
            session,
            enrollment_id=enrollment_id,
        )
    ]


@router.post(
    "/{enrollment_id}/progress",
    response_model=StudentProgressDetail,
    response_model_exclude_unset=True,
    status_code=status.HTTP_201_CREATED,
)
def create_progress(
    enrollment_id: int,
    session: SessionDep,
    progress_in: StudentProgressCreate,
    current_user: CurrentUserDep,
) -> StudentProgressDetail:
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

    return _progress_response(detail, enrollment, current_user)


@router.patch(
    "/{enrollment_id}/progress/{progress_id}",
    response_model=StudentProgressDetail,
    response_model_exclude_unset=True,
)
def update_progress(
    enrollment_id: int,
    progress_id: int,
    session: SessionDep,
    progress_in: StudentProgressUpdate,
    current_user: CurrentUserDep,
) -> StudentProgressDetail:
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

    return _progress_response(detail, enrollment, current_user)
