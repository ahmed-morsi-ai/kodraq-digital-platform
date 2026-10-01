from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.final_project import ProjectRequirement, TrainingProject
from app.models.track import Track
from app.models.user import User
from app.schemas.final_project import TrainingProjectCreate, TrainingProjectUpdate
from app.services.final_project_access import (
    ProjectConflictError,
    commit,
    require_manager,
    require_project_read,
    require_track_read,
)


def get_project(db: Session, project_id: int, *, lock=False) -> TrainingProject:
    """Internal retrieval; public CRUD operations authorize the actor."""
    stmt = (
        select(TrainingProject)
        .options(selectinload(TrainingProject.requirements))
        .where(TrainingProject.id == project_id)
    )
    if lock:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    project = db.scalar(stmt)
    if project is None:
        raise LookupError("Training project not found")
    return project


class CRUDTrainingProject:
    def get(self, db: Session, *, project_id: int, actor: User) -> TrainingProject:
        project = get_project(db, project_id)
        require_project_read(db, actor, project)
        return project

    def get_by_track(
        self, db: Session, *, track_id: int, actor: User
    ) -> TrainingProject:
        if db.get(Track, track_id) is None:
            raise LookupError("Track not found")
        require_track_read(db, actor, track_id)
        project = db.scalar(
            select(TrainingProject)
            .options(selectinload(TrainingProject.requirements))
            .where(TrainingProject.track_id == track_id)
        )
        if project is None:
            raise LookupError("Final project not found")
        require_project_read(db, actor, project)
        return project

    def create(
        self, db: Session, *, track_id: int, obj_in: TrainingProjectCreate, actor: User
    ) -> TrainingProject:
        require_manager(db, actor, track_id)
        # Lock the track so concurrent creates return one success and one conflict.
        if (
            db.scalar(select(Track).where(Track.id == track_id).with_for_update())
            is None
        ):
            raise LookupError("Track not found")
        if (
            db.scalar(
                select(TrainingProject.id).where(TrainingProject.track_id == track_id)
            )
            is not None
        ):
            raise ProjectConflictError("A final project already exists for this track.")
        data = TrainingProjectCreate.model_validate(obj_in.model_dump()).model_dump()
        requirements = data.pop("requirements")
        project = TrainingProject(
            track_id=track_id,
            **data,
            requirements=[ProjectRequirement(**item) for item in requirements],
        )
        db.add(project)
        return commit(db, project)

    def update(
        self,
        db: Session,
        *,
        project_id: int,
        obj_in: TrainingProjectUpdate,
        actor: User,
    ) -> TrainingProject:
        project = get_project(db, project_id, lock=True)
        require_manager(db, actor, project.track_id)
        data = TrainingProjectUpdate.model_validate(
            obj_in.model_dump(exclude_unset=True)
        ).model_dump(exclude_unset=True)
        requirements = data.pop("requirements", None)
        for field, value in data.items():
            setattr(project, field, value)
        if requirements is not None:
            project.requirements = [ProjectRequirement(**item) for item in requirements]
        return commit(db, project)

    def remove(self, db: Session, *, project_id: int, actor: User) -> None:
        project = get_project(db, project_id, lock=True)
        require_manager(db, actor, project.track_id)
        db.delete(project)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise


training_project = CRUDTrainingProject()
