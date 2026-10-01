from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import case, distinct, func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import SessionDep, get_current_active_admin
from app.core.admin_identity import PLATFORM_ADMIN_EMAIL
from app.models.ai import AIRequestLog
from app.models.enrollment import Enrollment, StudentProgress
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.role import Role
from app.models.track import Lesson, Track, TrackModule
from app.models.user import User
from app.schemas.track import (
    Lesson as LessonSchema,
    LessonQuizQuestion,
    Track as TrackSchema,
    TrackCurriculum,
    TrackModule as TrackModuleSchema,
)

router = APIRouter(prefix="/api/admin", tags=["admin-dashboard"])
AdminUserDep = Annotated[User, Depends(get_current_active_admin)]


class AdminUserSummary(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    is_superuser: bool
    subscription_active: bool
    joined_at: datetime
    progress_percentage: float


class AdminUserUpdate(BaseModel):
    role: Literal["student", "admin"] | None = None
    is_active: bool | None = None


class AdminUserRoleUpdate(BaseModel):
    role: Literal["student", "admin"]


class AdminTrackCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    description: str | None = None
    ordering: int = 0
    is_active: bool = True
    is_premium: bool = False
    price: Decimal = Decimal("0")
    currency: str = Field(default="EGP", min_length=3, max_length=3)


class AdminTrackUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    ordering: int | None = None
    is_active: bool | None = None
    is_premium: bool | None = None
    price: Decimal | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class AdminModuleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    ordering: int = 0
    is_active: bool = True


class AdminModuleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    ordering: int | None = None
    is_active: bool | None = None


class AdminLessonCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    content: str | None = None
    video_url: str | None = Field(default=None, max_length=512)
    ordering: int = 0
    quiz_data: list[LessonQuizQuestion] | None = None


class AdminLessonUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    content: str | None = None
    video_url: str | None = Field(default=None, max_length=512)
    ordering: int | None = None
    quiz_data: list[LessonQuizQuestion] | None = None


def _get_track(session: Session, track_id: int) -> Track:
    track = session.get(Track, track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    return track


def _get_module(session: Session, module_id: int) -> TrackModule:
    module = session.get(TrackModule, module_id)
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    return module


def _get_lesson(session: Session, lesson_id: int) -> Lesson:
    lesson = session.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@router.get("/stats")
def get_admin_stats(
    session: SessionDep,
    current_admin: AdminUserDep,
) -> dict:
    del current_admin
    now = datetime.now(UTC)
    yesterday = now - timedelta(days=1)
    last_week = now - timedelta(days=7)

    total_students = session.scalar(
        select(func.count(User.id))
        .join(Role, User.role_id == Role.id)
        .where(func.lower(Role.name) == "student")
    ) or 0
    active_tracks = session.scalar(
        select(func.count(Track.id)).where(Track.is_active.is_(True))
    ) or 0
    total_lessons = session.scalar(select(func.count(Lesson.id))) or 0
    total_progress = session.scalar(select(func.count(StudentProgress.id))) or 0
    completed_progress = session.scalar(
        select(func.count(StudentProgress.id)).where(
            func.lower(StudentProgress.status) == "completed"
        )
    ) or 0
    completion_rate = (
        round(completed_progress * 100 / total_progress, 1)
        if total_progress
        else 0.0
    )
    daily_active_users = session.scalar(
        select(func.count(distinct(Enrollment.user_id)))
        .join(StudentProgress, StudentProgress.enrollment_id == Enrollment.id)
        .where(StudentProgress.updated_at >= yesterday)
    ) or 0
    weekly_completions = session.scalar(
        select(func.count(StudentProgress.id)).where(
            func.lower(StudentProgress.status) == "completed",
            StudentProgress.updated_at >= last_week,
        )
    ) or 0
    average_response_ms = session.scalar(
        select(func.avg(AIRequestLog.latency_ms)).where(
            AIRequestLog.latency_ms.is_not(None)
        )
    )

    track_rows = session.execute(
        select(
            Track.id,
            Track.name,
            Track.ordering,
            func.avg(StudentProgress.progress_percentage),
        )
        .join(TrackModule, TrackModule.track_id == Track.id)
        .join(Lesson, Lesson.module_id == TrackModule.id)
        .join(StudentProgress, StudentProgress.lesson_id == Lesson.id)
        .where(Track.is_active.is_(True))
        .group_by(Track.id, Track.name, Track.ordering)
        .order_by(Track.ordering, Track.id)
        .limit(3)
    ).all()

    engagement = []
    for month_offset in range(5, -1, -1):
        month_index = now.month - 1 - month_offset
        year = now.year + month_index // 12
        month = month_index % 12 + 1
        month_start = datetime(year, month, 1, tzinfo=UTC)
        if month == 12:
            next_month = datetime(year + 1, 1, 1, tzinfo=UTC)
        else:
            next_month = datetime(year, month + 1, 1, tzinfo=UTC)
        active_count = session.scalar(
            select(func.count(distinct(Enrollment.user_id)))
            .join(StudentProgress, StudentProgress.enrollment_id == Enrollment.id)
            .where(
                StudentProgress.updated_at >= month_start,
                StudentProgress.updated_at < next_month,
            )
        ) or 0
        engagement.append(
            {"month": month_start.strftime("%b"), "active_users": active_count}
        )

    try:
        session.execute(select(1))
        database_health = "online"
    except Exception:
        database_health = "degraded"

    return {
        "total_users": total_students,
        "total_students": total_students,
        "active_tracks": active_tracks,
        "total_lessons": total_lessons,
        "completion_rate": completion_rate,
        "daily_active_users": daily_active_users,
        "active_sessions": daily_active_users,
        "completion_velocity": weekly_completions,
        "average_response_ms": round(float(average_response_ms), 1)
        if average_response_ms is not None
        else None,
        "system_health": "online" if database_health == "online" else "degraded",
        "engagement": engagement,
        "track_completion": [
            {
                "track_id": row[0],
                "track_name": row[1],
                "ordering": row[2],
                "completion_rate": round(float(row[3] or 0), 1),
            }
            for row in track_rows
        ],
    }


@router.get("/users", response_model=list[AdminUserSummary])
def list_admin_users(
    session: SessionDep,
    current_admin: AdminUserDep,
    search: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AdminUserSummary]:
    del current_admin
    statement = (
        select(User, Role.name)
        .join(Role, User.role_id == Role.id)
        .where(func.lower(Role.name).in_(("student", "admin")))
        .order_by(User.created_at.desc(), User.id.desc())
    )
    if search and search.strip():
        needle = f"%{search.strip()}%"
        statement = statement.where(
            User.full_name.ilike(needle) | User.email.ilike(needle)
        )
    rows = session.execute(statement.offset(skip).limit(limit)).all()
    user_ids = [user.id for user, _ in rows]
    progress_by_user: dict[int, float] = {}
    active_subscription_user_ids: set[int] = set()
    if user_ids:
        aggregates = session.execute(
            select(
                Enrollment.user_id,
                func.avg(StudentProgress.progress_percentage),
            )
            .join(StudentProgress, StudentProgress.enrollment_id == Enrollment.id)
            .where(Enrollment.user_id.in_(user_ids))
            .group_by(Enrollment.user_id)
        ).all()
        progress_by_user = {
            user_id: round(float(progress or 0), 1)
            for user_id, progress in aggregates
        }
        active_subscription_user_ids = set(
            session.scalars(
                select(distinct(Enrollment.user_id)).where(
                    Enrollment.user_id.in_(user_ids),
                    func.lower(Enrollment.status) == "active",
                )
            )
        )

    return [
        AdminUserSummary(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=role_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            subscription_active=user.id in active_subscription_user_ids,
            joined_at=user.created_at,
            progress_percentage=progress_by_user.get(user.id, 0),
        )
        for user, role_name in rows
    ]


@router.patch("/users/{user_id}", response_model=AdminUserSummary)
def update_admin_user(
    user_id: int,
    payload: AdminUserUpdate,
    session: SessionDep,
    current_admin: AdminUserDep,
) -> AdminUserSummary:
    target = session.scalar(
        select(User).options(selectinload(User.role_rel)).where(User.id == user_id)
    )
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No user changes provided")
    if target.id == current_admin.id and (
        changes.get("is_active") is False or changes.get("role") == "student"
    ):
        raise HTTPException(status_code=400, detail="You cannot remove your own admin access")
    if changes.get("role") == "admin" and target.email.casefold() != PLATFORM_ADMIN_EMAIL:
        raise HTTPException(
            status_code=400,
            detail=f"Only {PLATFORM_ADMIN_EMAIL} can be the platform administrator",
        )
    if "role" in changes:
        role = session.scalar(select(Role).where(func.lower(Role.name) == changes["role"]))
        if role is None:
            role = Role(name=changes["role"])
            session.add(role)
            session.flush()
        target.role_id = role.id
        target.is_superuser = (
            changes["role"] == "admin"
            and target.email.casefold() == PLATFORM_ADMIN_EMAIL
        )
    if "is_active" in changes:
        target.is_active = changes["is_active"]

    session.commit()
    session.refresh(target)
    progress_percentage = session.scalar(
        select(func.avg(StudentProgress.progress_percentage))
        .join(Enrollment, StudentProgress.enrollment_id == Enrollment.id)
        .where(Enrollment.user_id == target.id)
    )
    subscription_active = session.scalar(
        select(func.count(Enrollment.id)).where(
            Enrollment.user_id == target.id,
            func.lower(Enrollment.status) == "active",
        )
    ) or 0
    return AdminUserSummary(
        id=target.id,
        email=target.email,
        full_name=target.full_name,
        role=target.role_rel.name if target.role_rel else "student",
        is_active=target.is_active,
        is_superuser=target.is_superuser,
        subscription_active=subscription_active > 0,
        joined_at=target.created_at,
        progress_percentage=round(float(progress_percentage or 0), 1),
    )


@router.patch("/users/{user_id}/role", response_model=AdminUserSummary)
def update_admin_user_role(
    user_id: int,
    payload: AdminUserRoleUpdate,
    session: SessionDep,
    current_admin: AdminUserDep,
) -> AdminUserSummary:
    return update_admin_user(
        user_id,
        AdminUserUpdate(role=payload.role),
        session,
        current_admin,
    )


@router.post("/users/{user_id}/activate-subscription")
def activate_user_subscription(
    user_id: int,
    session: SessionDep,
    current_admin: AdminUserDep,
) -> dict:
    del current_admin
    target = session.scalar(
        select(User).options(selectinload(User.role_rel)).where(User.id == user_id)
    )
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    role_name = target.role_rel.name.casefold() if target.role_rel else ""
    if role_name != "student":
        raise HTTPException(status_code=400, detail="Subscriptions can only be activated for students")

    enrollments = list(
        session.scalars(select(Enrollment).where(Enrollment.user_id == target.id))
    )
    for enrollment in enrollments:
        enrollment.status = "active"
    target.is_active = True
    session.commit()
    return {
        "user_id": target.id,
        "is_active": target.is_active,
        "subscription_active": bool(enrollments),
        "activated_enrollments": len(enrollments),
    }


@router.get("/content/tracks", response_model=list[TrackCurriculum])
def list_content_tracks(
    session: SessionDep,
    current_admin: AdminUserDep,
) -> list[TrackCurriculum]:
    del current_admin
    tracks = session.scalars(
        select(Track)
        .options(
            selectinload(Track.modules).selectinload(TrackModule.lessons),
            selectinload(Track.modules).selectinload(TrackModule.resources),
        )
        .order_by(Track.ordering, Track.id)
    ).all()
    return [TrackCurriculum.model_validate(track, from_attributes=True) for track in tracks]


@router.post("/content/tracks", response_model=TrackSchema, status_code=201)
def create_content_track(
    payload: AdminTrackCreate,
    session: SessionDep,
    current_admin: AdminUserDep,
) -> Track:
    del current_admin
    existing = session.scalar(
        select(Track).where((Track.slug == payload.slug) | (Track.name == payload.name))
    )
    if existing:
        raise HTTPException(status_code=409, detail="Track name or slug already exists")
    track = Track(**payload.model_dump())
    session.add(track)
    session.commit()
    session.refresh(track)
    return track


@router.patch("/content/tracks/{track_id}", response_model=TrackSchema)
def update_content_track(
    track_id: int,
    payload: AdminTrackUpdate,
    session: SessionDep,
    current_admin: AdminUserDep,
) -> Track:
    del current_admin
    track = _get_track(session, track_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No track changes provided")
    if "slug" in changes or "name" in changes:
        name = changes.get("name", track.name)
        slug = changes.get("slug", track.slug)
        conflict = session.scalar(
            select(Track).where(
                Track.id != track.id,
                (Track.name == name) | (Track.slug == slug),
            )
        )
        if conflict:
            raise HTTPException(status_code=409, detail="Track name or slug already exists")
    for key, value in changes.items():
        setattr(track, key, value)
    session.commit()
    session.refresh(track)
    return track


@router.delete("/content/tracks/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_content_track(
    track_id: int,
    session: SessionDep,
    current_admin: AdminUserDep,
) -> Response:
    del current_admin
    track = _get_track(session, track_id)
    # Preserve learner history while removing the track from public discovery.
    track.is_active = False
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/content/tracks/{track_id}/modules", response_model=TrackModuleSchema, status_code=201)
def create_content_module(
    track_id: int,
    payload: AdminModuleCreate,
    session: SessionDep,
    current_admin: AdminUserDep,
) -> TrackModule:
    del current_admin
    _get_track(session, track_id)
    module = TrackModule(track_id=track_id, **payload.model_dump())
    session.add(module)
    session.commit()
    session.refresh(module)
    return module


@router.patch("/content/modules/{module_id}", response_model=TrackModuleSchema)
def update_content_module(
    module_id: int,
    payload: AdminModuleUpdate,
    session: SessionDep,
    current_admin: AdminUserDep,
) -> TrackModule:
    del current_admin
    module = _get_module(session, module_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No module changes provided")
    for key, value in changes.items():
        setattr(module, key, value)
    session.commit()
    session.refresh(module)
    return module


@router.delete("/content/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_content_module(
    module_id: int,
    session: SessionDep,
    current_admin: AdminUserDep,
) -> Response:
    del current_admin
    module = _get_module(session, module_id)
    session.delete(module)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/content/modules/{module_id}/lessons", response_model=LessonSchema, status_code=201)
def create_content_lesson(
    module_id: int,
    payload: AdminLessonCreate,
    session: SessionDep,
    current_admin: AdminUserDep,
) -> Lesson:
    del current_admin
    _get_module(session, module_id)
    lesson = Lesson(
        module_id=module_id,
        **payload.model_dump(exclude={"quiz_data"}),
        quiz_data=[item.model_dump() for item in payload.quiz_data]
        if payload.quiz_data is not None
        else None,
    )
    session.add(lesson)
    session.commit()
    session.refresh(lesson)
    return lesson


@router.patch("/content/lessons/{lesson_id}", response_model=LessonSchema)
def update_content_lesson(
    lesson_id: int,
    payload: AdminLessonUpdate,
    session: SessionDep,
    current_admin: AdminUserDep,
) -> Lesson:
    del current_admin
    lesson = _get_lesson(session, lesson_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No lesson changes provided")
    if "quiz_data" in changes and changes["quiz_data"] is not None:
        changes["quiz_data"] = [item.model_dump() for item in payload.quiz_data or []]
    for key, value in changes.items():
        setattr(lesson, key, value)
    session.commit()
    session.refresh(lesson)
    return lesson


@router.delete("/content/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_content_lesson(
    lesson_id: int,
    session: SessionDep,
    current_admin: AdminUserDep,
) -> Response:
    del current_admin
    lesson = _get_lesson(session, lesson_id)
    session.delete(lesson)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/logs")
def get_admin_logs(
    session: SessionDep,
    current_admin: AdminUserDep,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    del current_admin
    activities: list[dict] = []

    enrollments = session.execute(
        select(Enrollment, User.full_name, Track.name)
        .join(User, Enrollment.user_id == User.id)
        .join(Track, Enrollment.track_id == Track.id)
        .order_by(Enrollment.created_at.desc())
        .limit(limit)
    ).all()
    for enrollment, full_name, track_name in enrollments:
        activities.append(
            {
                "kind": "enrollment",
                "created_at": enrollment.created_at,
                "summary": f"{full_name} enrolled in {track_name}",
                "status": enrollment.status,
            }
        )

    quiz_attempts = session.execute(
        select(QuizAttempt, User.full_name, Quiz.title)
        .join(User, QuizAttempt.user_id == User.id)
        .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
        .order_by(QuizAttempt.started_at.desc())
        .limit(limit)
    ).all()
    for attempt, full_name, quiz_title in quiz_attempts:
        activities.append(
            {
                "kind": "quiz_submission",
                "created_at": attempt.completed_at or attempt.started_at,
                "summary": f"{full_name} submitted {quiz_title}",
                "status": attempt.status,
                "score": attempt.score,
            }
        )

    ai_logs = session.execute(
        select(AIRequestLog, User.full_name)
        .outerjoin(User, AIRequestLog.user_id == User.id)
        .order_by(AIRequestLog.created_at.desc())
        .limit(limit)
    ).all()
    for request_log, full_name in ai_logs:
        activities.append(
            {
                "kind": "ai_request",
                "created_at": request_log.created_at,
                "summary": f"{full_name or 'Deleted user'} used {request_log.request_type}",
                "status": "success" if request_log.success else "failed",
                "latency_ms": request_log.latency_ms,
                "total_tokens": request_log.total_tokens,
            }
        )

    activities.sort(key=lambda item: item["created_at"], reverse=True)
    ai_totals = session.execute(
        select(
            func.count(AIRequestLog.id),
            func.sum(case((AIRequestLog.success.is_(False), 1), else_=0)),
            func.avg(AIRequestLog.latency_ms),
            func.sum(AIRequestLog.total_tokens),
        )
    ).one()
    return {
        "activities": activities[:limit],
        "ai_usage": {
            "requests": int(ai_totals[0] or 0),
            "failed_requests": int(ai_totals[1] or 0),
            "average_latency_ms": round(float(ai_totals[2]), 1)
            if ai_totals[2] is not None
            else None,
            "total_tokens": int(ai_totals[3] or 0),
        },
    }