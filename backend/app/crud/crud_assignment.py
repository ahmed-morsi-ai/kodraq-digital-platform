from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.assignment import Assignment
from app.models.track import Lesson, TrackModule
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate


class CRUDAssignment(CRUDBase[Assignment, AssignmentCreate, AssignmentUpdate]):
    def get_by_context(
        self,
        db: Session,
        *,
        track_id: int | None = None,
        module_id: int | None = None,
        lesson_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Assignment]:
        filters = []
        if track_id is not None:
            filters.append(
                or_(
                    Assignment.track_id == track_id,
                    Assignment.module.has(TrackModule.track_id == track_id),
                    Assignment.lesson.has(
                        Lesson.module.has(TrackModule.track_id == track_id)
                    ),
                )
            )
        if module_id is not None:
            filters.append(
                or_(
                    Assignment.module_id == module_id,
                    Assignment.lesson.has(Lesson.module_id == module_id),
                )
            )
        if lesson_id is not None:
            filters.append(Assignment.lesson_id == lesson_id)

        stmt = (
            select(Assignment)
            .where(*filters)
            .order_by(Assignment.ordering, Assignment.id)
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()


assignment = CRUDAssignment(Assignment)


def create_assignment(db: Session, obj_in: AssignmentCreate) -> Assignment:
    return assignment.create(db, obj_in=obj_in)


def get_assignment(db: Session, assignment_id: int) -> Assignment | None:
    return assignment.get(db, assignment_id)


def get_assignments_by_context(
    db: Session,
    track_id: int | None = None,
    module_id: int | None = None,
    lesson_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Assignment]:
    return assignment.get_by_context(
        db,
        track_id=track_id,
        module_id=module_id,
        lesson_id=lesson_id,
        skip=skip,
        limit=limit,
    )


def update_assignment(
    db: Session,
    db_obj: Assignment,
    obj_in: AssignmentUpdate,
) -> Assignment:
    return assignment.update(db, db_obj=db_obj, obj_in=obj_in)


def delete_assignment(db: Session, assignment_id: int) -> Assignment | None:
    return assignment.remove(db, id=assignment_id)
