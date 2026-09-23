from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.models.final_project import ProjectRequirement, TrainingProject
from app.models.track import Track


def _create_track(db_session):
    track = Track(
        name="Final Project Model Track",
        slug="final-project-model-track",
        description="Final project model test track",
    )
    db_session.add(track)
    db_session.flush()
    return track


def test_training_project_creation_and_relationships(db_session):
    track = _create_track(db_session)

    project = TrainingProject(
        track_id=track.id,
        title="Build a Production API",
        description="Final capstone implementation.",
    )
    project.requirements.extend(
        [
            ProjectRequirement(
                description="Implement authentication.",
                is_mandatory=True,
                order=1,
            ),
            ProjectRequirement(
                description="Provide automated tests.",
                is_mandatory=False,
                order=2,
            ),
        ]
    )

    db_session.add(project)
    db_session.commit()

    assert project.id is not None
    assert project.track_id == track.id
    assert project.track.id == track.id
    assert project.passing_score == 75
    assert project.is_active is True
    assert [requirement.order for requirement in project.requirements] == [1, 2]
    assert TrainingProject.requirements.property.lazy == "selectin"


def test_training_project_requires_existing_track(db_session):
    project = TrainingProject(
        track_id=999999999,
        title="Orphan Final Project",
        description="Should not persist without a valid track.",
    )
    db_session.add(project)

    try:
        db_session.commit()
    except IntegrityError:
        db_session.rollback()
    else:
        raise AssertionError("TrainingProject persisted without a valid track")


def test_deleting_training_project_cascades_to_requirements(db_session):
    track = _create_track(db_session)

    project = TrainingProject(
        track_id=track.id,
        title="Cascade Test Project",
        description="Cascade deletion verification.",
    )
    project.requirements.extend(
        [
            ProjectRequirement(
                description="Requirement one",
                is_mandatory=True,
                order=1,
            ),
            ProjectRequirement(
                description="Requirement two",
                is_mandatory=True,
                order=2,
            ),
        ]
    )

    db_session.add(project)
    db_session.commit()

    project_id = project.id

    db_session.execute(
        delete(TrainingProject).where(TrainingProject.id == project_id)
    )
    db_session.commit()

    remaining = db_session.execute(
        select(ProjectRequirement).where(
            ProjectRequirement.project_id == project_id
        )
    ).scalars().all()

    assert remaining == []
