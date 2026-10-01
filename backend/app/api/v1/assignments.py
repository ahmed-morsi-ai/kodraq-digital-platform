from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select

from app.api.deps import (
    SessionDep,
    get_current_active_assignment_manager,
    get_current_active_user,
)
from app.crud.crud_assignment import (
    assignment as crud_assignment,
)
from app.models.assignment import Assignment
from app.models.enrollment import Enrollment
from app.models.track_instructor import TrackInstructor
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


def _accessible_track_ids(session: SessionDep, user: UserModel) -> list[int] | None:
    """None grants administrator access; an empty list grants no track access."""
    role_name = user.role_rel.name.casefold() if user.role_rel else ""
    if user.is_superuser or role_name == "admin":
        return None
    if role_name == "instructor":
        stmt = select(TrackInstructor.track_id).where(
            TrackInstructor.instructor_id == user.id,
        )
    else:
        stmt = select(Enrollment.track_id).where(
            Enrollment.user_id == user.id,
            Enrollment.status == "active",
        )
    return list(session.scalars(stmt).all())


def _require_track_access(
    track_id: int | None, allowed_track_ids: list[int] | None
) -> None:
    if allowed_track_ids is not None and track_id not in allowed_track_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this assignment's track.",
        )


def _require_assignment_access(
    session: SessionDep,
    assignment: Assignment,
    allowed_track_ids: list[int] | None,
) -> None:
    if allowed_track_ids is None:
        return
    try:
        track_id = crud_assignment.resolve_track_id(
            session,
            track_id=assignment.track_id,
            module_id=assignment.module_id,
            lesson_id=assignment.lesson_id,
        )
    except (LookupError, ValueError) as error:
        # Legacy rows with inconsistent ancestry have no safe non-admin scope.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this assignment's track.",
        ) from error
    _require_track_access(track_id, allowed_track_ids)


def _get_assignment_or_404(session: SessionDep, assignment_id: int) -> Assignment:
    assignment = crud_assignment.get(session, id=assignment_id)
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )
    return assignment


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
    allowed_track_ids = _accessible_track_ids(session, current_user)
    try:
        track_id = crud_assignment.resolve_track_id(
            session,
            track_id=assignment_in.track_id,
            module_id=assignment_in.module_id,
            lesson_id=assignment_in.lesson_id,
        )
        _require_track_access(track_id, allowed_track_ids)
        return crud_assignment.create(session, obj_in=assignment_in)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("", response_model=list[AssignmentResponse])
def read_assignments(
    session: SessionDep,
    current_user: CurrentUserDep,
    track_id: int | None = None,
    module_id: int | None = None,
    lesson_id: int | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=0)] = 100,
) -> list[Assignment]:
    assignments = crud_assignment.get_by_context(
        session,
        track_id=track_id,
        module_id=module_id,
        lesson_id=lesson_id,
        skip=skip,
        limit=limit,
        allowed_track_ids=_accessible_track_ids(session, current_user),
    )
    return list(assignments)


@router.get("/{assignment_id}", response_model=AssignmentResponse)
def read_assignment(
    assignment_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Assignment:
    assignment = _get_assignment_or_404(session, assignment_id)
    _require_assignment_access(
        session,
        assignment,
        _accessible_track_ids(session, current_user),
    )
    return assignment


@router.patch("/{assignment_id}", response_model=AssignmentResponse)
def update_assignment(
    assignment_id: int,
    session: SessionDep,
    assignment_in: AssignmentUpdate,
    current_user: CurrentAssignmentManagerDep,
) -> Assignment:
    assignment = _get_assignment_or_404(session, assignment_id)
    allowed_track_ids = _accessible_track_ids(session, current_user)
    _require_assignment_access(session, assignment, allowed_track_ids)
    changes = assignment_in.model_dump(exclude_unset=True)
    try:
        track_id = crud_assignment.resolve_track_id(
            session,
            track_id=changes.get("track_id", assignment.track_id),
            module_id=changes.get("module_id", assignment.module_id),
            lesson_id=changes.get("lesson_id", assignment.lesson_id),
        )
        _require_track_access(track_id, allowed_track_ids)
        return crud_assignment.update(
            session,
            db_obj=assignment,
            obj_in=assignment_in,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: int,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
) -> Response:
    assignment = _get_assignment_or_404(session, assignment_id)
    _require_assignment_access(
        session,
        assignment,
        _accessible_track_ids(session, current_user),
    )
    crud_assignment.remove(session, id=assignment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
