from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    SessionDep,
    get_current_active_assignment_manager,
    get_current_active_user,
)
from app.crud.crud_graduation import (
    evaluate_graduation,
    get_graduation_evaluation,
    get_latest_graduation_evaluation,
)
from app.models.track import Track
from app.models.user import User
from app.schemas.graduation import GraduationEvaluationResponse

router = APIRouter()

CurrentUserDep = Annotated[
    User,
    Depends(get_current_active_user),
]

CurrentAssignmentManagerDep = Annotated[
    User,
    Depends(get_current_active_assignment_manager),
]


@router.get(
    "/status",
    response_model=GraduationEvaluationResponse,
)
def read_graduation_status(
    session: SessionDep,
    current_user: CurrentUserDep,
    user_id: int | None = None,
    track_id: int | None = None,
) -> GraduationEvaluationResponse:
    requested_user_id = user_id or current_user.id
    is_manager = current_user.is_superuser or (
        current_user.role_rel is not None
        and current_user.role_rel.name.casefold() in {"admin", "instructor"}
    )
    if requested_user_id != current_user.id and not is_manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own graduation status.",
        )

    evaluation = (
        get_graduation_evaluation(
            session,
            user_id=requested_user_id,
            track_id=track_id,
        )
        if track_id is not None
        else get_latest_graduation_evaluation(session, requested_user_id)
    )
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Graduation evaluation not found",
        )
    return evaluation


@router.post(
    "/evaluate/{user_id}",
    response_model=GraduationEvaluationResponse,
    status_code=status.HTTP_201_CREATED,
)
def evaluate_user_graduation(
    user_id: int,
    session: SessionDep,
    current_user: CurrentAssignmentManagerDep,
    track_id: int,
) -> GraduationEvaluationResponse:
    del current_user
    if session.get(User, user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if session.get(Track, track_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found",
        )
    return evaluate_graduation(session, user_id=user_id, track_id=track_id)
