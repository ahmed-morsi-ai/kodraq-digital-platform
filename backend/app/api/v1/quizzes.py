from __future__ import annotations

from contextlib import contextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import PositiveInt

from app.api.deps import SessionDep, get_current_active_user
from app.crud.crud_assignment import assignment as curriculum
from app.crud.crud_quiz import quiz as crud_quiz
from app.crud.crud_quiz_attempt import quiz_attempt as crud_attempt
from app.models.user import User
from app.schemas.quiz import QuizResultResponse, StudentQuizResponse
from app.schemas.quiz_attempt import QuizAttemptResponse, QuizAttemptSubmit
from app.services.quiz_access import require_quiz, require_track

router = APIRouter()
attempt_router = APIRouter()
CurrentUserDep = Annotated[User, Depends(get_current_active_user)]
PageOffset = Annotated[int, Query(ge=0)]
PageLimit = Annotated[int, Query(ge=1, le=100)]


@contextmanager
def _http_errors():
    try:
        yield
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("", response_model=list[StudentQuizResponse])
def list_available_quizzes(
    session: SessionDep,
    current_user: CurrentUserDep,
    track_id: PositiveInt | None = None,
    module_id: PositiveInt | None = None,
    lesson_id: PositiveInt | None = None,
    skip: PageOffset = 0,
    limit: PageLimit = 100,
):
    if track_id is None and module_id is None and lesson_id is None:
        raise HTTPException(
            status_code=400, detail="Quiz discovery requires a track_id or lesson_id."
        )
    with _http_errors():
        owner = curriculum.resolve_track_id(
            session, track_id=track_id, module_id=module_id, lesson_id=lesson_id
        )
        require_track(session, current_user, owner)
        quizzes = crud_quiz.get_by_context(
            session,
            track_id=track_id,
            module_id=module_id,
            lesson_id=lesson_id,
            skip=skip,
            limit=limit,
            active_only=True,
        )
        for quiz in quizzes:
            require_quiz(session, current_user, quiz)
        return quizzes


@router.get("/{quiz_id}", response_model=StudentQuizResponse)
def read_available_quiz(
    quiz_id: PositiveInt, session: SessionDep, current_user: CurrentUserDep
):
    with _http_errors():
        quiz = crud_quiz.get(session, id=quiz_id)
        if quiz is None or not quiz.is_active:
            raise LookupError("Quiz not found")
        require_quiz(session, current_user, quiz)
        return quiz


@router.post("/{quiz_id}/attempts", response_model=QuizAttemptResponse, status_code=201)
def start_quiz_attempt(
    quiz_id: PositiveInt, session: SessionDep, current_user: CurrentUserDep
):
    with _http_errors():
        return crud_attempt.create_for_user(
            session, quiz_id=quiz_id, actor=current_user
        )


@router.get("/{quiz_id}/attempts", response_model=list[QuizAttemptResponse])
def list_quiz_attempts(
    quiz_id: PositiveInt,
    session: SessionDep,
    current_user: CurrentUserDep,
    skip: PageOffset = 0,
    limit: PageLimit = 100,
):
    with _http_errors():
        return crud_attempt.get_multi_by_quiz(
            session, quiz_id=quiz_id, actor=current_user, skip=skip, limit=limit
        )


@attempt_router.post("/{attempt_id}/submit", response_model=QuizAttemptResponse)
def submit_quiz_attempt(
    attempt_id: PositiveInt,
    submission: QuizAttemptSubmit,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    with _http_errors():
        return crud_attempt.submit(
            session, attempt_id=attempt_id, actor=current_user, obj_in=submission
        )


@attempt_router.get("/{attempt_id}/results", response_model=QuizResultResponse)
def read_quiz_attempt_results(
    attempt_id: PositiveInt, session: SessionDep, current_user: CurrentUserDep
):
    with _http_errors():
        return crud_attempt.build_result(
            session, attempt_id=attempt_id, actor=current_user
        )


@attempt_router.get("/{attempt_id}", response_model=QuizAttemptResponse)
def read_quiz_attempt(
    attempt_id: PositiveInt, session: SessionDep, current_user: CurrentUserDep
):
    with _http_errors():
        return crud_attempt.get_for_user(
            session, attempt_id=attempt_id, actor=current_user
        )
