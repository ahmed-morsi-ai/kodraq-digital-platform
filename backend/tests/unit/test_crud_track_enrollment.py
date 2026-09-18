from __future__ import annotations

from app.crud.crud_enrollment import enrollment, student_progress
from app.crud.crud_track import lesson, resource, track, track_module
from app.models.user import User
from app.schemas.enrollment import (
    EnrollmentCreate,
    EnrollmentDetail,
    StudentProgressCreate,
    StudentProgressUpdate,
)
from app.schemas.track import (
    LessonCreate,
    ResourceCreate,
    TrackCreate,
    TrackCurriculum,
    TrackModuleCreate,
)


def test_track_curriculum_crud(db_session):
    created_track = track.create(
        db_session,
        obj_in=TrackCreate(
            name="Python Backend",
            slug="python-backend",
            description="Backend engineering track",
            ordering=1,
        ),
    )

    assert created_track.id is not None

    fetched_by_slug = track.get_by_slug(
        db_session,
        slug="python-backend",
    )

    assert fetched_by_slug is not None
    assert fetched_by_slug.id == created_track.id

    created_module = track_module.create(
        db_session,
        obj_in=TrackModuleCreate(
            track_id=created_track.id,
            title="FastAPI Fundamentals",
            description="Build production APIs",
            ordering=1,
        ),
    )

    created_lesson = lesson.create(
        db_session,
        obj_in=LessonCreate(
            module_id=created_module.id,
            title="Dependency Injection",
            content="FastAPI dependency injection",
            ordering=1,
        ),
    )

    created_resource = resource.create_for_module(
        db_session,
        module_id=created_module.id,
        obj_in=ResourceCreate(
            title="FastAPI Guide",
            file_url="https://example.com/fastapi.pdf",
            resource_type="pdf",
        ),
    )

    assert created_lesson.id is not None
    assert created_resource.id is not None

    module_content = track_module.get_with_content(
        db_session,
        id=created_module.id,
    )

    assert module_content is not None
    assert len(module_content.lessons) == 1
    assert len(module_content.resources) == 1

    curriculum = track.get_with_curriculum(
        db_session,
        id=created_track.id,
    )

    assert curriculum is not None
    assert len(curriculum.modules) == 1
    assert len(curriculum.modules[0].lessons) == 1
    assert len(curriculum.modules[0].resources) == 1

    curriculum_schema = TrackCurriculum.model_validate(curriculum)

    assert curriculum_schema.id == created_track.id
    assert curriculum_schema.modules[0].lessons[0].id == created_lesson.id
    assert curriculum_schema.modules[0].resources[0].id == created_resource.id


def test_enrollment_and_progress_crud(db_session):
    created_track = track.create(
        db_session,
        obj_in=TrackCreate(
            name="AI Engineering",
            slug="ai-engineering",
            description="AI engineering track",
            ordering=1,
        ),
    )

    created_module = track_module.create(
        db_session,
        obj_in=TrackModuleCreate(
            track_id=created_track.id,
            title="Machine Learning Foundations",
            ordering=1,
        ),
    )

    created_lesson = lesson.create(
        db_session,
        obj_in=LessonCreate(
            module_id=created_module.id,
            title="Supervised Learning",
            ordering=1,
        ),
    )

    student = User(
        email="crud-enrollment@example.com",
        hashed_password="test-hash",
        full_name="CRUD Test Student",
        is_active=True,
        is_superuser=False,
    )

    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    created_enrollment = enrollment.create_for_user(
        db_session,
        user_id=student.id,
        obj_in=EnrollmentCreate(
            track_id=created_track.id,
            status="active",
        ),
    )

    assert created_enrollment.id is not None
    assert created_enrollment.user_id == student.id
    assert created_enrollment.track_id == created_track.id

    fetched_enrollment = enrollment.get_by_user_and_track(
        db_session,
        user_id=student.id,
        track_id=created_track.id,
    )

    assert fetched_enrollment is not None
    assert fetched_enrollment.id == created_enrollment.id

    created_progress = student_progress.create(
        db_session,
        obj_in=StudentProgressCreate(
            enrollment_id=created_enrollment.id,
            lesson_id=created_lesson.id,
            status="in_progress",
            progress_percentage=50,
        ),
    )

    assert created_progress.id is not None
    assert created_progress.progress_percentage == 50

    progress_lookup = student_progress.get_by_enrollment_and_lesson(
        db_session,
        enrollment_id=created_enrollment.id,
        lesson_id=created_lesson.id,
    )

    assert progress_lookup is not None
    assert progress_lookup.id == created_progress.id

    updated_progress = student_progress.update(
        db_session,
        db_obj=created_progress,
        obj_in=StudentProgressUpdate(
            status="completed",
            progress_percentage=100,
        ),
    )

    assert updated_progress.status == "completed"
    assert updated_progress.progress_percentage == 100

    enrollment_detail = enrollment.get_detail(
        db_session,
        id=created_enrollment.id,
    )

    assert enrollment_detail is not None
    assert enrollment_detail.track.id == created_track.id
    assert len(enrollment_detail.progress) == 1
    assert enrollment_detail.progress[0].lesson.id == created_lesson.id

    enrollment_schema = EnrollmentDetail.model_validate(enrollment_detail)

    assert enrollment_schema.id == created_enrollment.id
    assert enrollment_schema.track is not None
    assert enrollment_schema.track.id == created_track.id
    assert len(enrollment_schema.progress) == 1
    assert enrollment_schema.progress[0].progress_percentage == 100


def test_active_track_query(db_session):
    track.create(
        db_session,
        obj_in=TrackCreate(
            name="Inactive Track",
            slug="inactive-track",
            is_active=False,
            ordering=1,
        ),
    )

    active_track = track.create(
        db_session,
        obj_in=TrackCreate(
            name="Active Track",
            slug="active-track",
            is_active=True,
            ordering=2,
        ),
    )

    active_tracks = track.get_active(db_session)

    assert len(active_tracks) == 1
    assert active_tracks[0].id == active_track.id
    assert active_tracks[0].slug == "active-track"
