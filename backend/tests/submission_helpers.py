from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.core.security import create_access_token
from app.models.assignment import Assignment
from app.models.enrollment import Enrollment
from app.models.role import Role
from app.models.submission import Submission
from app.models.track import Lesson, Track, TrackModule
from app.models.track_instructor import TrackInstructor
from app.models.user import User


def headers(data, role="student"):
    return {"Authorization": f"Bearer {create_access_token(data.users[role].id)}"}


def make_submission(db, data, *, scope="track", owner="student", state="DRAFT"):
    submission = Submission(
        assignment=data.assignments[scope],
        user=data.users[owner],
        status=state,
        content="Original work",
        github_url="https://github.com/student/work",
    )
    db.add(submission)
    db.flush()
    return submission


@pytest.fixture
def submission_data(db_session):
    roles = {
        name: Role(name=value)
        for name, value in {
            "student": "Student",
            "instructor": "INSTRUCTOR",
            "admin": "Admin",
            "employee": "employee",
        }.items()
    }
    users = {
        name: User(
            email=f"submission-{name}@example.com",
            full_name=name,
            hashed_password="unused-test-hash",
            role_rel=roles.get(name, roles["student"]),
            is_superuser=name == "superuser",
            is_active=name != "inactive",
        )
        for name in (
            "student",
            "other",
            "instructor",
            "admin",
            "superuser",
            "employee",
            "inactive",
        )
    }
    data = SimpleNamespace(users=users, assignments={})
    for name in ("a", "b"):
        track = Track(name=f"Submission track {name}", slug=f"submission-track-{name}")
        module = TrackModule(track=track, title=f"Module {name}")
        lesson = Lesson(module=module, title=f"Lesson {name}")
        db_session.add_all([track, module, lesson])
        setattr(data, name, SimpleNamespace(track=track, module=module, lesson=lesson))
    db_session.add_all(users.values())
    db_session.flush()
    data.enrollment = Enrollment(
        user_id=users["student"].id,
        track_id=data.a.track.id,
        status="active",
        enrolled_at=datetime.now(UTC),
    )
    db_session.add_all(
        [
            data.enrollment,
            Enrollment(
                user_id=users["other"].id,
                track_id=data.b.track.id,
                status="active",
                enrolled_at=datetime.now(UTC),
            ),
            TrackInstructor(
                instructor_id=users["instructor"].id, track_id=data.a.track.id
            ),
        ]
    )
    contexts = {
        "track": {"track_id": data.a.track.id},
        "module": {"module_id": data.a.module.id},
        "lesson": {"lesson_id": data.a.lesson.id},
        "full": {
            "track_id": data.a.track.id,
            "module_id": data.a.module.id,
            "lesson_id": data.a.lesson.id,
        },
        "other": {"track_id": data.b.track.id},
        "unscoped": {},
        "inconsistent": {"track_id": data.a.track.id, "lesson_id": data.b.lesson.id},
        "inactive": {"track_id": data.a.track.id, "is_active": False},
    }
    for scope, context in contexts.items():
        assignment = Assignment(
            title=f"Assignment {scope}",
            description="Description",
            instructions="Instructions",
            difficulty="beginner",
            **context,
        )
        data.assignments[scope] = assignment
        db_session.add(assignment)
    db_session.flush()
    return data
