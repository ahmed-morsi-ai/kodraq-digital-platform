from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.crud.base import CRUDBase
from app.models.assignment import Assignment
from app.models.track import Lesson, Track, TrackModule
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate


class CRUDAssignment(CRUDBase[Assignment, AssignmentCreate, AssignmentUpdate]):
    def resolve_track_id(
        self,
        db: Session,
        *,
        track_id: int | None,
        module_id: int | None,
        lesson_id: int | None,
    ) -> int | None:
        """Validate the context and resolve its direct or inherited owning track."""
        with db.no_autoflush:
            track = db.get(Track, track_id) if track_id is not None else None
            module = db.get(TrackModule, module_id) if module_id is not None else None
            lesson = db.get(Lesson, lesson_id) if lesson_id is not None else None

            if track_id is not None and track is None:
                raise LookupError("Track not found")
            if module_id is not None and module is None:
                raise LookupError("Track module not found")
            if lesson_id is not None and lesson is None:
                raise LookupError("Lesson not found")

            if module and track and module.track_id != track.id:
                raise ValueError("module_id does not belong to track_id.")
            if lesson and module and lesson.module_id != module.id:
                raise ValueError("lesson_id does not belong to module_id.")
            if lesson and track:
                lesson_module = module or db.get(TrackModule, lesson.module_id)
                if lesson_module is None:
                    raise LookupError("Track module not found")
                if lesson_module.track_id != track.id:
                    raise ValueError("lesson_id does not belong to track_id.")

            if track is not None:
                return track.id
            if module is not None:
                return module.track_id
            if lesson is not None:
                return lesson.module.track_id
            return None

    def create(self, db: Session, *, obj_in: AssignmentCreate) -> Assignment:
        payload = AssignmentCreate.model_validate(obj_in.model_dump())
        self.resolve_track_id(
            db,
            track_id=payload.track_id,
            module_id=payload.module_id,
            lesson_id=payload.lesson_id,
        )
        return super().create(db, obj_in=payload)

    def update(
        self,
        db: Session,
        *,
        db_obj: Assignment,
        obj_in: AssignmentUpdate | dict[str, Any],
    ) -> Assignment:
        changes = (
            obj_in
            if isinstance(obj_in, dict)
            else obj_in.model_dump(exclude_unset=True)
        )
        payload = AssignmentUpdate.model_validate(changes)
        changes = payload.model_dump(exclude_unset=True)
        self.resolve_track_id(
            db,
            track_id=changes.get("track_id", db_obj.track_id),
            module_id=changes.get("module_id", db_obj.module_id),
            lesson_id=changes.get("lesson_id", db_obj.lesson_id),
        )
        if not changes:
            return db_obj
        return super().update(db, db_obj=db_obj, obj_in=payload)

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Assignment]:
        return self.get_by_context(db, skip=skip, limit=limit)

    def get_by_context(
        self,
        db: Session,
        *,
        track_id: int | None = None,
        module_id: int | None = None,
        lesson_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
        allowed_track_ids: Sequence[int] | None = None,
    ) -> Sequence[Assignment]:
        if skip < 0 or limit < 0:
            raise ValueError("skip and limit must be non-negative")

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

        stmt = select(Assignment).where(*filters)
        if allowed_track_ids is not None:
            stmt = self._scope_to_tracks(stmt, allowed_track_ids)
        stmt = (
            stmt.order_by(Assignment.ordering, Assignment.id).offset(skip).limit(limit)
        )
        return db.execute(stmt).scalars().all()

    def _scope_to_tracks(
        self,
        stmt: Select[tuple[Assignment]],
        allowed_track_ids: Sequence[int],
    ) -> Select[tuple[Assignment]]:
        """Scope before pagination, excluding unscoped or inconsistent legacy rows."""
        module = aliased(TrackModule)
        lesson = aliased(Lesson)
        lesson_module = aliased(TrackModule)
        owning_track = func.coalesce(
            Assignment.track_id,
            module.track_id,
            lesson_module.track_id,
        )
        return (
            stmt.outerjoin(module, Assignment.module_id == module.id)
            .outerjoin(lesson, Assignment.lesson_id == lesson.id)
            .outerjoin(lesson_module, lesson.module_id == lesson_module.id)
            .where(
                owning_track.in_(allowed_track_ids),
                or_(Assignment.module_id.is_(None), module.track_id == owning_track),
                or_(
                    Assignment.lesson_id.is_(None),
                    lesson_module.track_id == owning_track,
                ),
                or_(
                    Assignment.module_id.is_(None),
                    Assignment.lesson_id.is_(None),
                    lesson.module_id == Assignment.module_id,
                ),
            )
        )


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
