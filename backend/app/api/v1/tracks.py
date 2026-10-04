from __future__ import annotations

import json
import math
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import PositiveInt, ValidationError
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
from app.models.track import Lesson as LessonModel
from app.models.track import Track, TrackModule as TrackModuleModel
from app.models.track_assignment_config import TrackAssignmentConfig
from app.models.user import User as UserModel
from app.schemas.track import (
    Lesson,
    LessonCreate,
    Resource,
    ResourceCreate,
    TrackCreate,
    TrackCurriculum,
    TrackCurriculumPreview,
    TrackModule,
    TrackModuleCreate,
    TrackSummary,
    LessonQuizQuestion,
    LessonQuizResult,
    LessonQuizResultAnswer,
    LessonQuizSubmission,
    LessonQuizPrompt,
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


def _has_curriculum_access(session, current_user: UserModel, track_id: int) -> bool:
    # Preserve the deployed curriculum entitlement: superuser or active enrollment.
    if current_user.is_superuser:
        return True
    enrollment = session.scalar(
        select(Enrollment).where(
            Enrollment.user_id == current_user.id,
            Enrollment.track_id == track_id,
        )
    )
    return enrollment is not None and enrollment.status == "active"


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


@router.get(
    "/{track_id}/curriculum",
    response_model=TrackCurriculumPreview,
)
def read_track_curriculum(
    track_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> JSONResponse:
    track = crud_track.get_with_curriculum(
        session,
        id=track_id,
    )

    if not track or not track.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found",
        )

    track_payload = TrackCurriculum.model_validate(track, from_attributes=True)
    authorized = _has_curriculum_access(session, current_user, track.id)

    preview = TrackCurriculumPreview(
        name=track_payload.name,
        slug=track_payload.slug,
        description=track_payload.description,
        ordering=track_payload.ordering,
        is_active=track_payload.is_active,
        is_premium=track_payload.is_premium,
        price=track_payload.price,
        currency=track_payload.currency,
        id=track_payload.id,
        modules=[
            {
                "id": module.id,
                "track_id": module.track_id,
                "title": module.title,
                "description": module.description,
                "ordering": module.ordering,
                "is_active": module.is_active,
                "lessons": [
                    {
                        "id": lesson.id,
                        "module_id": lesson.module_id,
                        "title": lesson.title,
                        "description": lesson.description,
                        "ordering": lesson.ordering,
                        **(
                            {
                                "content": lesson.content,
                                "video_url": lesson.video_url,
                                "quiz_data": [
                                    LessonQuizPrompt(
                                        id=question.id,
                                        question=question.question,
                                        options=question.options,
                                    )
                                    for question in lesson.quiz_data or []
                                ],
                            }
                            if authorized
                            else {}
                        ),
                    }
                    for lesson in module.lessons
                ],
                "resources": [
                    {
                        "id": resource.id,
                        "module_id": resource.module_id,
                        "title": resource.title,
                        "resource_type": resource.resource_type,
                        **({"file_url": resource.file_url} if authorized else {}),
                    }
                    for resource in module.resources
                ],
            }
            for module in track_payload.modules
        ],
    )
    return JSONResponse(content=preview.model_dump(mode="json", exclude_unset=True))


@router.post(
    "/{track_id}/lessons/{lesson_id}/quiz/submit",
    response_model=LessonQuizResult,
)
def submit_lesson_quiz(
    track_id: PositiveInt,
    lesson_id: PositiveInt,
    submission: LessonQuizSubmission,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> LessonQuizResult:
    lesson = session.scalar(
        select(LessonModel)
        .join(TrackModuleModel, LessonModel.module_id == TrackModuleModel.id)
        .join(Track, TrackModuleModel.track_id == Track.id)
        .where(
            LessonModel.id == lesson_id,
            TrackModuleModel.track_id == track_id,
            Track.is_active.is_(True),
        )
    )
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found.")
    if not _has_curriculum_access(session, current_user, track_id):
        raise HTTPException(status_code=403, detail="An active enrollment is required.")

    raw_questions = lesson.quiz_data
    if isinstance(raw_questions, str):
        try:
            raw_questions = json.loads(raw_questions)
        except json.JSONDecodeError:
            raw_questions = None
    try:
        questions = [
            LessonQuizQuestion.model_validate(item)
            for item in raw_questions or []
        ]
    except (TypeError, ValidationError):
        questions = []
    if not questions:
        raise HTTPException(status_code=404, detail="Lesson quiz not found.")

    answer_by_id = {answer.question_id: answer for answer in submission.answers}
    question_ids = {question.id for question in questions}
    if set(answer_by_id) != question_ids:
        raise HTTPException(
            status_code=422,
            detail="Submit exactly one answer for each lesson quiz question.",
        )

    results = []
    score = 0
    for question in questions:
        answer = answer_by_id[question.id]
        if answer.selected_index >= len(question.options):
            raise HTTPException(
                status_code=422,
                detail="A selected option is invalid for this question.",
            )
        correct = answer.selected_index == question.correct_index
        score += int(correct)
        results.append(
            LessonQuizResultAnswer(
                question_id=question.id,
                selected_index=answer.selected_index,
                correct_index=question.correct_index,
                is_correct=correct,
                explanation=question.explanation,
            )
        )

    total = len(questions)
    return LessonQuizResult(
        score=score,
        total=total,
        percentage=math.floor(score * 100 / total + 0.5),
        answers=results,
    )


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
