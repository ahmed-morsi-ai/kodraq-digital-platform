from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import (
    SessionDep,
    get_current_active_assignment_manager,
    get_current_active_superuser,
    get_current_active_user,
)
from app.crud.crud_track import (
    lesson as crud_lesson,
)
from app.crud.crud_track import (
    resource as crud_resource,
)
from app.crud.crud_track import (
    track as crud_track,
)
from app.crud.crud_track import (
    track_module as crud_track_module,
)
from app.crud.crud_track_assignment_config import (
    track_assignment_config as crud_track_assignment_config,
)
from app.models.enrollment import Enrollment
from app.models.track import Track
from app.models.track_assignment_config import TrackAssignmentConfig
from app.models.user import User as UserModel
from app.schemas.track import (
    Lesson,
    LessonCreate,
    Resource,
    ResourceCreate,
    TrackCreate,
    TrackCurriculum,
    TrackModule,
    TrackModuleCreate,
    TrackSummary,
)
from app.schemas.track_assignment_config import (
    TrackAssignmentConfigResponse,
    TrackAssignmentConfigUpdate,
)

router = APIRouter()

CurrentSuperuserDep = Annotated[
    UserModel,
    Depends(get_current_active_superuser),
]

CurrentUserDep = Annotated[
    UserModel,
    Depends(get_current_active_user),
]

CurrentAssignmentConfigManagerDep = Annotated[
    UserModel,
    Depends(get_current_active_assignment_manager),
]


@router.get("", response_model=list[TrackSummary])
def read_tracks(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    tracks = crud_track.get_active(
        session,
        skip=skip,
        limit=limit,
    )
    return list(tracks)


@router.get("/{track_id}/curriculum", response_model=TrackCurriculum)
def read_track_curriculum(
    track_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TrackCurriculum:
    track = crud_track.get_with_curriculum(
        session,
        id=track_id,
    )

    if not track or not track.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found",
        )

    enrollment = session.scalar(
        select(Enrollment).where(
            Enrollment.user_id == current_user.id,
            Enrollment.track_id == track_id,
        )
    )

    track_payload = TrackCurriculum.model_validate(track, from_attributes=True)

    if not current_user.is_superuser and (
        enrollment is None or enrollment.status != "active"
    ):
        track_payload = track_payload.model_copy(
            update={
                "modules": [
                    module.model_copy(
                        update={
                            "lessons": [
                                lesson.model_copy(
                                    update={
                                        "content": (
                                            "هذا المحتوى مقفل. "
                                            "يرجى الاشتراك في المسار "
                                            "لتتمكن من عرض تفاصيل الدرس."
                                        )
                                    }
                                )
                                for lesson in module.lessons
                            ]
                        }
                    )
                    for module in track_payload.modules
                ]
            }
        )

    return track_payload


@router.get(
    "/{track_id}/assignment-config/",
    response_model=TrackAssignmentConfigResponse,
)
def read_track_assignment_config(
    track_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TrackAssignmentConfig:
    del current_user

    track = crud_track.get(session, id=track_id)
    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found",
        )

    return crud_track_assignment_config.get_or_create_default(
        session,
        track_id=track_id,
    )


def _update_track_assignment_config(
    track_id: int,
    session: SessionDep,
    config_in: TrackAssignmentConfigUpdate,
    current_user: UserModel,
) -> TrackAssignmentConfig:
    del current_user

    track = crud_track.get(session, id=track_id)
    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found",
        )

    config = crud_track_assignment_config.get_or_create_default(
        session,
        track_id=track_id,
    )
    return crud_track_assignment_config.update(
        session,
        db_obj=config,
        obj_in=config_in,
    )


@router.patch(
    "/{track_id}/assignment-config/",
    response_model=TrackAssignmentConfigResponse,
)
def patch_track_assignment_config(
    track_id: int,
    session: SessionDep,
    config_in: TrackAssignmentConfigUpdate,
    current_user: CurrentAssignmentConfigManagerDep,
) -> TrackAssignmentConfig:
    return _update_track_assignment_config(
        track_id,
        session,
        config_in,
        current_user,
    )


@router.put(
    "/{track_id}/assignment-config/",
    response_model=TrackAssignmentConfigResponse,
)
def put_track_assignment_config(
    track_id: int,
    session: SessionDep,
    config_in: TrackAssignmentConfigUpdate,
    current_user: CurrentAssignmentConfigManagerDep,
) -> TrackAssignmentConfig:
    return _update_track_assignment_config(
        track_id,
        session,
        config_in,
        current_user,
    )


@router.post(
    "",
    response_model=TrackSummary,
    status_code=status.HTTP_201_CREATED,
)
def create_track(
    session: SessionDep,
    track_in: TrackCreate,
    current_user: CurrentSuperuserDep,
) -> Track:
    del current_user

    existing = session.execute(
        select(Track).where(
            (Track.slug == track_in.slug) | (Track.name == track_in.name)
        )
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A track with this name or slug already exists.",
        )

    return crud_track.create(
        session,
        obj_in=track_in,
    )


@router.post(
    "/{track_id}/modules",
    response_model=TrackModule,
    status_code=status.HTTP_201_CREATED,
)
def create_track_module(
    track_id: int,
    session: SessionDep,
    module_in: TrackModuleCreate,
    current_user: CurrentSuperuserDep,
) -> TrackModule:
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

    if module_in.track_id != track_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="track_id does not match the URL track_id.",
        )

    return crud_track_module.create(
        session,
        obj_in=module_in,
    )


@router.post(
    "/modules/{module_id}/lessons",
    response_model=Lesson,
    status_code=status.HTTP_201_CREATED,
)
def create_lesson(
    module_id: int,
    session: SessionDep,
    lesson_in: LessonCreate,
    current_user: CurrentSuperuserDep,
) -> Lesson:
    del current_user

    module = crud_track_module.get(
        session,
        id=module_id,
    )

    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track module not found",
        )

    if lesson_in.module_id != module_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="module_id does not match the URL module_id.",
        )

    return crud_lesson.create(
        session,
        obj_in=lesson_in,
    )


@router.post(
    "/modules/{module_id}/resources",
    response_model=Resource,
    status_code=status.HTTP_201_CREATED,
)
def create_resource(
    module_id: int,
    session: SessionDep,
    resource_in: ResourceCreate,
    current_user: CurrentSuperuserDep,
) -> Resource:
    del current_user

    module = crud_track_module.get(
        session,
        id=module_id,
    )

    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track module not found",
        )

    return crud_resource.create_for_module(
        session,
        module_id=module_id,
        obj_in=resource_in,
    )
