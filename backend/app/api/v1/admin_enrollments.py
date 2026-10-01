from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import SessionDep, get_current_active_admin
from app.models.enrollment import Enrollment
from app.models.user import User
from app.schemas.enrollment import (
    AdminEnrollmentResponse,
    AdminEnrollmentStatusUpdate,
)

router = APIRouter()


CurrentAdminDep = Annotated[User, Depends(get_current_active_admin)]


def _admin_enrollment_response(
    enrollment: Enrollment,
) -> AdminEnrollmentResponse:
    return AdminEnrollmentResponse(
        id=enrollment.id,
        user_id=enrollment.user_id,
        student_name=enrollment.user.full_name,
        student_email=enrollment.user.email,
        track_id=enrollment.track_id,
        track_name=enrollment.track.name,
        status=enrollment.status,
        enrolled_at=enrollment.enrolled_at,
    )


def _get_enrollment_query():
    return select(Enrollment).options(
        joinedload(Enrollment.user),
        joinedload(Enrollment.track),
    )


@router.get(
    "/enrollments/",
    response_model=list[AdminEnrollmentResponse],
    include_in_schema=False,
)
@router.get(
    "/enrollments",
    response_model=list[AdminEnrollmentResponse],
)
def list_admin_enrollments(
    session: SessionDep,
    current_admin: CurrentAdminDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[AdminEnrollmentResponse]:
    del current_admin
    enrollments = session.execute(
        _get_enrollment_query()
        .order_by(Enrollment.enrolled_at.desc(), Enrollment.id.desc())
        .offset(skip)
        .limit(limit)
    ).scalars().unique().all()
    return [_admin_enrollment_response(enrollment) for enrollment in enrollments]


@router.patch(
    "/enrollments/{enrollment_id}/status",
    response_model=AdminEnrollmentResponse,
)
def update_admin_enrollment_status(
    enrollment_id: int,
    status_in: AdminEnrollmentStatusUpdate,
    session: SessionDep,
    current_admin: CurrentAdminDep,
) -> AdminEnrollmentResponse:
    del current_admin
    enrollment = session.execute(
        _get_enrollment_query().where(Enrollment.id == enrollment_id)
    ).scalars().unique().one_or_none()
    if enrollment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )

    enrollment.status = status_in.status
    session.commit()

    updated_enrollment = session.execute(
        _get_enrollment_query().where(Enrollment.id == enrollment_id)
    ).scalars().unique().one()
    return _admin_enrollment_response(updated_enrollment)