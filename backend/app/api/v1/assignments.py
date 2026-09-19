from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import (
    SessionDep,
    get_current_active_assignment_manager,
    get_current_active_user,
)
from app.crud.crud_assignment import (
    assignment as crud_assignment,
)
from app.models.assignment import Assignment
from app.models.track import Lesson, Track, TrackModule
from app.models.user import User as UserModel
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentResponse,
    AssignmentUpdate,
)

router = APIRouter()

CurrentUserDep = Annotated[
    UserModel,
    Depends(get_current_active_user),
]

CurrentAssignmentManagerDep = Annotated[
    UserModel,
    Depends(get_current_active_assignment_manager),
]


def _validate_context_references(
    session: SessionDep,
    *,
    track_id: int | None,
    module_id: int | None,
    lesson_id: int | None,
) -> None:
    track = session.get(Track, track_id) if track_id is not None else None
    module = session.get(TrackModule, module_id) if module_id is not None else None
    lesson = session.get(Lesson, lesson_id) if lesson_id is not None else None

    if track_id is not None and track is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found",
        )
    if module_id is not None and module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track module not found",
        )
    if lesson_id is not None and lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    if module and track and module.track_id != track.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="module_id does not belong to track_id.",
        )

    if lesson and module and lesson.module_id != module.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="lesson_id does not belong to module_id.",
        )

    if lesson and track:
        lesson_module = module or session.get(TrackModule, lesson.module_id)
        if lesson_module and lesson_module.track_id != track.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="lesson_id does not belong to track_id.",
            )


@router.post(
    "",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    session: SessionDep,
    assignment_in: AssignmentCreate,
    current_user: CurrentAssignmentManagerDep,
) -> Assignment:
    del current_user

    _validate_context_references(
        session,
        track_id=assignment_in.track_id,
        module_id=assignment_in.module_id,
        lesson_id=assignment_in.lesson_id,
    )

    return crud_assignment.create(session, obj_in=assignment_in)


@router.get("", response_model=list[AssignmentResponse])
def read_assignments(
    session: SessionDep,
    current_user: CurrentUserDep,
    track_id: int | None = None,
    module_id: int | None = None,
    lesson_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Assignment]:
    del current_user

    assignments = crud_assignment.get_by_context(
        session,
        track_id=track_id,
        module_id=module_id,
        lesson_id=lesson_id,
        skip=skip,
        limit=limit,
    )
    return list(assignments)


@router.get("/{assignment_id}", response_model=AssignmentResponse)
def read_assignment(
    assignment_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Assignment:
    del current_user

    assignment = crud_assignment.get(session, id=assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    return assignment


@router.patch("/{assignment_id}", response_model=AssignmentResponse)
def update_assignment(
    assignment_id: int,
    session: SessionDep,
    assignment_in: AssignmentUpdate,
    current_user: CurrentAssignmentManagerDep,
) -> Assignment:
    del current_user

    assignment = crud_assignment.get(session, id=assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    update_data = assignment_in.model_dump(exclude_unset=True)
    _validate_context_references(
        session,
        track_id=update_data.get("track_id", assignment.track_id),
        module_id=update_data.get("module_id", assignment.module_id),
        lesson_id=update_data.get("lesson_id", assignment.lesson_id),
    )

    return crud_assignment.update(
        session,
        db_obj=assignment,
        obj_in=assignment_in,
    )


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: int,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
) -> Response:
    del current_user

    deleted = crud_assignment.remove(session, id=assignment_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
