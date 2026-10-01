from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import select

from app.core.security import create_access_token
from app.models.enrollment import Enrollment
from app.models.final_project import TrainingProject, ProjectRequirement
from app.models.role import Role
from app.models.track import Track
from app.models.track_instructor import TrackInstructor
from app.models.user import User


def seed_final_projects(db):
    tag = uuid4().hex
    roles = {}
    for name in ("admin", "instructor", "student", "employee"):
        roles[name] = db.scalar(select(Role).where(Role.name == name))
        if roles[name] is None:
            roles[name] = Role(name=name)
            db.add(roles[name])
    users = {}
    for name, role in (
        ("admin", "admin"),
        ("instructor", "instructor"),
        ("foreign", "instructor"),
        ("student", "student"),
        ("other", "student"),
        ("outsider", "student"),
        ("employee", "employee"),
    ):
        users[name] = User(
            email=f"{name}-{tag}@example.com",
            full_name=name,
            hashed_password="unused",
            is_active=True,
            role_rel=roles[role],
        )
        db.add(users[name])
    users["superuser"] = User(
        email=f"super-{tag}@example.com",
        full_name="Super",
        hashed_password="unused",
        is_active=True,
        is_superuser=True,
    )
    db.add(users["superuser"])
    tracks = [
        Track(name=f"Capstone {tag} {i}", slug=f"capstone-{tag}-{i}") for i in range(3)
    ]
    db.add_all(tracks)
    db.flush()
    for name in ("student", "other", "employee", "instructor"):
        db.add(
            Enrollment(
                user_id=users[name].id,
                track_id=tracks[0].id,
                status="active",
                enrolled_at=datetime.now(UTC),
            )
        )
    db.add_all(
        [
            TrackInstructor(
                track_id=tracks[0].id, instructor_id=users["instructor"].id
            ),
            TrackInstructor(
                track_id=tracks[2].id, instructor_id=users["instructor"].id
            ),
            TrackInstructor(track_id=tracks[1].id, instructor_id=users["foreign"].id),
        ]
    )
    projects = [
        TrainingProject(
            title=f"Project {i}",
            track_id=tracks[i].id,
            passing_score=75,
            requirements=[
                ProjectRequirement(description="Later", order=2),
                ProjectRequirement(description="First", order=0),
                ProjectRequirement(
                    description="Same order", order=0, is_mandatory=False
                ),
            ],
        )
        for i in range(2)
    ]
    db.add_all(projects)
    db.commit()
    return SimpleNamespace(
        users=users, tracks=tracks, project=projects[0], foreign_project=projects[1]
    )


def headers(user):
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}
