from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import SessionDep, get_current_active_user
from app.models.graduation import GraduationResult
from app.models.user import User
from app.schemas.graduation import (
    GraduationEligibilityResponse,
    GraduationFinalizeRequest,
    GraduationResultResponse,
)
from app.services import graduation

router = APIRouter()
CurrentUser = Annotated[User, Depends(get_current_active_user)]
PositivePath = Annotated[int, Path(gt=0)]
PositiveQuery = Annotated[int, Query(gt=0)]


def _error(error):
    code = (
        403
        if isinstance(error, PermissionError)
        else 404
        if isinstance(error, LookupError)
        else 409
    )
    return HTTPException(status_code=code, detail=str(error))


@router.get("/status", response_model=GraduationEligibilityResponse)
def read_status(
    session: SessionDep,
    current_user: CurrentUser,
    track_id: PositiveQuery,
    user_id: Annotated[int | None, Query(gt=0)] = None,
):
    try:
        return graduation.read_eligibility(
            session,
            actor=current_user,
            user_id=user_id or current_user.id,
            track_id=track_id,
        )
    except (PermissionError, LookupError, ValueError) as error:
        raise _error(error) from error


@router.post("/evaluate/{user_id}", response_model=GraduationEligibilityResponse)
def evaluate_student(
    user_id: PositivePath,
    track_id: PositiveQuery,
    session: SessionDep,
    current_user: CurrentUser,
    payload: GraduationFinalizeRequest | None = None,
):
    try:
        graduation.require_manager(session, current_user, track_id)
        return graduation.read_eligibility(
            session, actor=current_user, user_id=user_id, track_id=track_id
        )
    except (PermissionError, LookupError, ValueError) as error:
        raise _error(error) from error


@router.post("/finalize/{user_id}", response_model=GraduationResultResponse)
def finalize_student(
    user_id: PositivePath,
    track_id: PositiveQuery,
    session: SessionDep,
    current_user: CurrentUser,
    payload: GraduationFinalizeRequest | None = None,
):
    try:
        return graduation.finalize_graduation(
            session, actor=current_user, user_id=user_id, track_id=track_id
        )
    except (PermissionError, LookupError, ValueError) as error:
        raise _error(error) from error


@router.get("/results", response_model=list[GraduationResultResponse])
def list_results(
    track_id: PositiveQuery,
    session: SessionDep,
    current_user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    try:
        graduation.require_manager(session, current_user, track_id)
    except PermissionError as error:
        raise _error(error) from error
    return list(
        session.scalars(
            select(GraduationResult)
            .options(selectinload(GraduationResult.checks))
            .where(GraduationResult.track_id == track_id)
            .order_by(GraduationResult.id.desc())
            .offset(skip)
            .limit(limit)
        )
    )


@router.get("/results/{result_id}", response_model=GraduationResultResponse)
def read_result(
    result_id: PositivePath, session: SessionDep, current_user: CurrentUser
):
    result = session.get(GraduationResult, result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Graduation result not found.")
    try:
        graduation.require_read(
            session, current_user, result.student_id, result.track_id
        )
    except PermissionError as error:
        raise _error(error) from error
    return result
