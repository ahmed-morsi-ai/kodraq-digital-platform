from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import (
    SessionDep,
    get_current_active_assignment_manager,
    get_current_active_user,
)
from app.crud.crud_quiz import quiz as crud_quiz
from app.crud.crud_quiz_attempt import quiz_attempt as crud_quiz_attempt
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt, QuizAttemptStatus
from app.models.track_instructor import TrackInstructor
from app.models.user import User as UserModel
from app.schemas.quiz import (
    QuizResultResponse,
    StudentQuizResponse,
)
from app.schemas.quiz_attempt import (
    QuizAttemptResponse,
    QuizAttemptSubmit,
)

router = APIRouter()
attempt_router = APIRouter()



CurrentUserDep = Annotated[
    UserModel,
    Depends(get_current_active_user),
]

CurrentAssignmentManagerDep = Annotated[
    UserModel,
    Depends(get_current_active_assignment_manager),
]


@router.get(
    "",
    response_model=list[StudentQuizResponse],
)
def list_available_quizzes(
    session: SessionDep,
    current_user: CurrentUserDep,
    track_id: int | None = None,
    lesson_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Quiz]:
    del current_user

    if track_id is None and lesson_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quiz discovery requires a track_id or lesson_id.",
        )

    if lesson_id is not None and track_id is None:
        quizzes = crud_quiz.get_multi_by_lesson(
            session,
            lesson_id=lesson_id,
            skip=skip,
            limit=limit,
        )
    else:
        quizzes = crud_quiz.get_multi_by_track(
            session,
            track_id=track_id,
            skip=skip,
            limit=limit,
        )

        if lesson_id is not None:
            quizzes = [
                quiz for quiz in quizzes if quiz.lesson_id == lesson_id
            ]

    return [
        quiz for quiz in quizzes if quiz.is_active
    ]


@router.get(
    "/{quiz_id}",
    response_model=StudentQuizResponse,
)
def read_available_quiz(
    quiz_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Quiz:
    del current_user

    quiz = _get_quiz_or_404(session, quiz_id)

    if not quiz.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        )

    return quiz


def _is_assignment_manager(user: UserModel) -> bool:
    if user.is_superuser:
        return True

    role_name = user.role_rel.name.casefold() if user.role_rel else ""
    return role_name in {"admin", "instructor"}


def _get_quiz_or_404(session: SessionDep, quiz_id: int) -> Quiz:
    quiz = crud_quiz.get(session, id=quiz_id)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        )
    return quiz


def _get_attempt_or_404(
    session: SessionDep,
    attempt_id: int,
) -> QuizAttempt:
    attempt = crud_quiz_attempt.get(session, id=attempt_id)
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz attempt not found",
        )
    return attempt


@router.post(
    "/{quiz_id}/attempts",
    response_model=QuizAttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_quiz_attempt(
    quiz_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> QuizAttempt:
    quiz = _get_quiz_or_404(session, quiz_id)
    if not quiz.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        )

    try:
        return crud_quiz_attempt.create_for_user(
            session,
            quiz_id=quiz_id,
            user_id=current_user.id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from None


@router.get(
    "/{quiz_id}/attempts",
    response_model=list[QuizAttemptResponse],
)
def list_quiz_attempts(
    quiz_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
) -> list[QuizAttempt]:
    _get_quiz_or_404(session, quiz_id)
    user_id = None if _is_assignment_manager(current_user) else current_user.id
    attempts = crud_quiz_attempt.get_multi_by_quiz(
        session,
        quiz_id=quiz_id,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )
    return list(attempts)


@attempt_router.post(
    "/{attempt_id}/submit",
    response_model=QuizAttemptResponse,
)
def submit_quiz_attempt(
    attempt_id: int,
    submission: QuizAttemptSubmit,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> QuizAttempt:
    attempt = _get_attempt_or_404(session, attempt_id)
    if attempt.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the attempt owner can submit answers.",
        )
    if attempt.status != QuizAttemptStatus.IN_PROGRESS.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quiz attempt has already been completed.",
        )

    try:
        return crud_quiz_attempt.submit(
            session,
            db_obj=attempt,
            answers=submission.answers,
            is_flagged=submission.is_flagged,
            flag_reason=submission.flag_reason,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from None


@attempt_router.get(
    "/{attempt_id}/results",
    response_model=QuizResultResponse,
)
def read_quiz_attempt_results(
    attempt_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> dict[str, object]:
    attempt = _get_attempt_or_404(session, attempt_id)

    if attempt.status != QuizAttemptStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quiz attempt results are available only after completion.",
        )

    role_name = (
        current_user.role_rel.name.casefold()
        if current_user.role_rel
        else ""
    )

    if current_user.is_superuser or role_name == "admin":
        return crud_quiz_attempt.build_result(db_obj=attempt)

    if role_name == "instructor":
        if attempt.quiz.track_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Quiz is not assigned to a track.",
            )

        assigned = session.scalar(
            select(TrackInstructor.track_id).where(
                TrackInstructor.track_id == attempt.quiz.track_id,
                TrackInstructor.instructor_id == current_user.id,
            )
        )
        if assigned is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Instructor is not assigned to this quiz track.",
            )

        return crud_quiz_attempt.build_result(db_obj=attempt)

    if attempt.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this quiz result.",
        )

    return crud_quiz_attempt.build_result(db_obj=attempt)


@attempt_router.get(
    "/{attempt_id}",
    response_model=QuizAttemptResponse,
)
def read_quiz_attempt(
    attempt_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> QuizAttempt:
    attempt = _get_attempt_or_404(session, attempt_id)
    if attempt.user_id != current_user.id and not _is_assignment_manager(
        current_user
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this quiz attempt.",
        )

    return attempt
