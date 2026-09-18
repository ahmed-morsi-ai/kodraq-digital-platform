from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.crud.base import CRUDBase
from app.models.enrollment import Enrollment, StudentProgress
from app.schemas.enrollment import (
    EnrollmentCreate,
    EnrollmentUpdate,
    StudentProgressCreate,
    StudentProgressUpdate,
)


class CRUDEnrollment(CRUDBase[Enrollment, EnrollmentCreate, EnrollmentUpdate]):
    def get_by_user_and_track(
        self,
        db: Session,
        *,
        user_id: int,
        track_id: int,
    ) -> Enrollment | None:
        stmt = select(Enrollment).where(
            Enrollment.user_id == user_id,
            Enrollment.track_id == track_id,
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_multi_by_user(
        self,
        db: Session,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Enrollment]:
        stmt = (
            select(Enrollment)
            .options(joinedload(Enrollment.track))
            .where(Enrollment.user_id == user_id)
            .order_by(Enrollment.id)
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().unique().all()

    def get_multi_by_track(
        self,
        db: Session,
        *,
        track_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Enrollment]:
        stmt = (
            select(Enrollment)
            .options(joinedload(Enrollment.user))
            .where(Enrollment.track_id == track_id)
            .order_by(Enrollment.id)
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().unique().all()

    def create_for_user(
        self,
        db: Session,
        *,
        user_id: int,
        obj_in: EnrollmentCreate,
    ) -> Enrollment:
        db_obj = Enrollment(
            user_id=user_id,
            track_id=obj_in.track_id,
            status=obj_in.status,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_detail(
        self,
        db: Session,
        *,
        id: int,
    ) -> Enrollment | None:
        stmt = (
            select(Enrollment)
            .options(
                joinedload(Enrollment.track),
                selectinload(Enrollment.progress).selectinload(
                    StudentProgress.lesson
                ),
            )
            .where(Enrollment.id == id)
        )
        return db.execute(stmt).scalars().unique().one_or_none()


class CRUDStudentProgress(
    CRUDBase[StudentProgress, StudentProgressCreate, StudentProgressUpdate]
):
    def get_by_enrollment_and_lesson(
        self,
        db: Session,
        *,
        enrollment_id: int,
        lesson_id: int,
    ) -> StudentProgress | None:
        stmt = select(StudentProgress).where(
            StudentProgress.enrollment_id == enrollment_id,
            StudentProgress.lesson_id == lesson_id,
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_multi_by_enrollment(
        self,
        db: Session,
        *,
        enrollment_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[StudentProgress]:
        stmt = (
            select(StudentProgress)
            .where(StudentProgress.enrollment_id == enrollment_id)
            .order_by(StudentProgress.id)
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()

    def get_detail(
        self,
        db: Session,
        *,
        id: int,
    ) -> StudentProgress | None:
        stmt = (
            select(StudentProgress)
            .options(selectinload(StudentProgress.lesson))
            .where(StudentProgress.id == id)
        )
        return db.execute(stmt).scalar_one_or_none()


enrollment = CRUDEnrollment(Enrollment)
student_progress = CRUDStudentProgress(StudentProgress)
