from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.track_assignment_config import TrackAssignmentConfig
from app.schemas.track_assignment_config import TrackAssignmentConfigUpdate


class CRUDTrackAssignmentConfig(
    CRUDBase[
        TrackAssignmentConfig,
        TrackAssignmentConfigUpdate,
        TrackAssignmentConfigUpdate,
    ]
):
    def get_by_track_id(
        self,
        db: Session,
        *,
        track_id: int,
    ) -> TrackAssignmentConfig | None:
        stmt = select(TrackAssignmentConfig).where(
            TrackAssignmentConfig.track_id == track_id
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_or_create_default(
        self,
        db: Session,
        *,
        track_id: int,
    ) -> TrackAssignmentConfig:
        config = self.get_by_track_id(db, track_id=track_id)
        if config:
            return config

        config = TrackAssignmentConfig(track_id=track_id)
        db.add(config)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            config = self.get_by_track_id(db, track_id=track_id)
            if config is None:
                raise
            return config

        db.refresh(config)
        return config


track_assignment_config = CRUDTrackAssignmentConfig(TrackAssignmentConfig)
