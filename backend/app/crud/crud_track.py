from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.crud.base import CRUDBase
from app.models.track import Lesson, Resource, Track, TrackModule
from app.schemas.track import (
    LessonCreate,
    ResourceCreate,
    TrackCreate,
    TrackModuleCreate,
)


class CRUDTrack(CRUDBase[Track, TrackCreate, BaseModel]):
    def get_by_slug(self, db: Session, *, slug: str) -> Track | None:
        stmt = select(Track).where(Track.slug == slug)
        return db.execute(stmt).scalar_one_or_none()

    def get_active(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Track]:
        stmt = (
            select(Track)
            .where(Track.is_active.is_(True))
            .order_by(Track.ordering, Track.id)
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()

    def get_with_curriculum(
        self,
        db: Session,
        *,
        id: int,
    ) -> Track | None:
        stmt = (
            select(Track)
            .options(
                selectinload(Track.modules).selectinload(TrackModule.lessons),
                selectinload(Track.modules).selectinload(TrackModule.resources),
            )
            .where(Track.id == id)
        )
        return db.execute(stmt).scalar_one_or_none()


class CRUDTrackModule(CRUDBase[TrackModule, TrackModuleCreate, BaseModel]):
    def get_multi_by_track(
        self,
        db: Session,
        *,
        track_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[TrackModule]:
        stmt = (
            select(TrackModule)
            .where(TrackModule.track_id == track_id)
            .order_by(TrackModule.ordering, TrackModule.id)
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()

    def get_with_content(
        self,
        db: Session,
        *,
        id: int,
    ) -> TrackModule | None:
        stmt = (
            select(TrackModule)
            .options(
                selectinload(TrackModule.lessons),
                selectinload(TrackModule.resources),
            )
            .where(TrackModule.id == id)
        )
        return db.execute(stmt).scalar_one_or_none()


class CRUDLesson(CRUDBase[Lesson, LessonCreate, BaseModel]):
    def get_multi_by_module(
        self,
        db: Session,
        *,
        module_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Lesson]:
        stmt = (
            select(Lesson)
            .where(Lesson.module_id == module_id)
            .order_by(Lesson.ordering, Lesson.id)
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()


class CRUDResource(CRUDBase[Resource, ResourceCreate, BaseModel]):
    def create_for_module(
        self,
        db: Session,
        *,
        module_id: int,
        obj_in: ResourceCreate,
    ) -> Resource:
        db_obj = Resource(
            module_id=module_id,
            title=obj_in.title,
            file_url=obj_in.file_url,
            resource_type=obj_in.resource_type,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_multi_by_module(
        self,
        db: Session,
        *,
        module_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Resource]:
        stmt = (
            select(Resource)
            .where(Resource.module_id == module_id)
            .order_by(Resource.id)
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()


track = CRUDTrack(Track)
track_module = CRUDTrackModule(TrackModule)
lesson = CRUDLesson(Lesson)
resource = CRUDResource(Resource)
