from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.final_project import ProjectRequirement, TrainingProject
from app.schemas.final_project import (
    TrainingProjectCreate,
    TrainingProjectUpdate,
)


def _project_query(project_id: int):
    return (
        select(TrainingProject)
        .options(selectinload(TrainingProject.requirements))
        .where(TrainingProject.id == project_id)
    )


class CRUDTrainingProject:
    def get(
        self,
        db: Session,
        *,
        project_id: int,
    ) -> TrainingProject | None:
        return db.execute(
            _project_query(project_id)
        ).scalar_one_or_none()

    def get_by_track(
        self,
        db: Session,
        *,
        track_id: int,
    ) -> TrainingProject | None:
        stmt = (
            select(TrainingProject)
            .options(selectinload(TrainingProject.requirements))
            .where(TrainingProject.track_id == track_id)
        )
        return db.execute(stmt).scalar_one_or_none()

    def create(
        self,
        db: Session,
        *,
        track_id: int,
        obj_in: TrainingProjectCreate,
    ) -> TrainingProject:
        data = obj_in.model_dump()
        requirements = data.pop("requirements", [])

        db_obj = TrainingProject(
            track_id=track_id,
            **data,
        )
        db_obj.requirements = [
            ProjectRequirement(**requirement)
            for requirement in requirements
        ]

        db.add(db_obj)

        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise ValueError(
                "A final project already exists for this track."
            ) from error

        return self.get(db, project_id=db_obj.id)  # type: ignore[return-value]

    def update(
        self,
        db: Session,
        *,
        db_obj: TrainingProject,
        obj_in: TrainingProjectUpdate,
    ) -> TrainingProject:
        data = obj_in.model_dump(exclude_unset=True)
        requirements = data.pop("requirements", None)

        for field, value in data.items():
            setattr(db_obj, field, value)

        if requirements is not None:
            db_obj.requirements = [
                ProjectRequirement(**requirement)
                for requirement in requirements
            ]

        db.add(db_obj)
        db.commit()

        return self.get(db, project_id=db_obj.id)  # type: ignore[return-value]

    def remove(
        self,
        db: Session,
        *,
        db_obj: TrainingProject,
    ) -> None:
        db.delete(db_obj)
        db.commit()


training_project = CRUDTrainingProject()
