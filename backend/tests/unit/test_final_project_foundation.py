from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError

from app.crud.crud_final_project import training_project as projects
from app.crud.crud_project_submission import project_submission as submissions
from app.models.final_project import TrainingProject, ProjectRequirement, ProjectReview
from app.models.project_submission import ProjectSubmission
from app.models.track import Track
from app.models.user import User
from app.schemas.final_project import (
    ProjectSubmissionCreate,
    ProjectSubmissionUpdate,
    ProjectReviewCreate,
    TrainingProjectUpdate,
)
from tests.final_project_helpers import seed_final_projects


@pytest.fixture
def data(db_session):
    return seed_final_projects(db_session)


def make_submission(db, data):
    record = submissions.create(
        db,
        project_id=data.project.id,
        actor=data.users["student"],
        obj_in=ProjectSubmissionCreate(github_url="https://github.com/owner/project"),
    )
    return submissions.update(
        db,
        submission_id=record.id,
        actor=data.users["student"],
        obj_in=ProjectSubmissionUpdate(status="SUBMITTED"),
    )


def test_bidirectional_relationships_and_stable_history(db_session, data):
    record = make_submission(db_session, data)
    first = submissions.create_review(
        db_session,
        submission_id=record.id,
        actor=data.users["instructor"],
        obj_in=ProjectReviewCreate(status_decision="UNDER_REVIEW", feedback="Started"),
    )
    final = submissions.create_review(
        db_session,
        submission_id=record.id,
        actor=data.users["admin"],
        obj_in=ProjectReviewCreate(score=80, feedback="Complete"),
    )
    first.created_at = final.created_at = datetime.now(UTC)
    db_session.commit()
    db_session.expire_all()
    assert record.project.id == data.project.id
    assert record.student.id == data.users["student"].id
    assert (
        record in record.student.project_submissions
        and record in data.project.submissions
    )
    assert final.submission.id == record.id and final in final.reviewer.project_reviews
    assert all(
        requirement.project.id == data.project.id
        for requirement in data.project.requirements
    )
    assert [review.id for review in record.reviews] == [first.id, final.id]


@pytest.mark.parametrize(
    "kind", ["track", "project", "submission", "student", "reviewer"]
)
def test_database_cascade_deletion(db_session, data, kind):
    record = make_submission(db_session, data)
    review = submissions.create_review(
        db_session,
        submission_id=record.id,
        actor=data.users["instructor"],
        obj_in=ProjectReviewCreate(score=80, feedback="Complete"),
    )
    project_id, record_id, review_id = data.project.id, record.id, review.id
    model, identifier = {
        "track": (Track, data.tracks[0].id),
        "project": (TrainingProject, project_id),
        "submission": (ProjectSubmission, record_id),
        "student": (User, data.users["student"].id),
        "reviewer": (User, data.users["instructor"].id),
    }[kind]
    db_session.execute(delete(model).where(model.id == identifier))
    db_session.commit()
    assert (
        db_session.scalar(select(ProjectReview.id).where(ProjectReview.id == review_id))
        is None
    )
    if kind != "reviewer":
        assert (
            db_session.scalar(
                select(ProjectSubmission.id).where(ProjectSubmission.id == record_id)
            )
            is None
        )
    if kind in {"track", "project"}:
        assert (
            db_session.scalar(
                select(ProjectRequirement.id).where(
                    ProjectRequirement.project_id == project_id
                )
            )
            is None
        )


@pytest.mark.parametrize(
    "kind",
    [
        "duplicate_project",
        "duplicate_submission",
        "passing_score",
        "blank_title",
        "blank_requirement",
        "null_requirement",
        "negative_order",
        "review_score",
        "review_decision",
        "submission_status",
        "missing_student",
        "missing_reviewer",
    ],
)
def test_database_rejects_invalid_records(db_session, data, kind):
    record = make_submission(db_session, data)
    statements = {
        "duplicate_project": (
            "INSERT INTO training_projects(track_id,title) VALUES (:track,'Duplicate')",
            {},
        ),
        "duplicate_submission": (
            "INSERT INTO project_submissions(project_id,student_id) VALUES (:project,:student)",
            {},
        ),
        "passing_score": (
            "UPDATE training_projects SET passing_score=101 WHERE id=:project",
            {},
        ),
        "blank_title": (
            "UPDATE training_projects SET title='   ' WHERE id=:project",
            {},
        ),
        "blank_requirement": (
            "INSERT INTO project_requirements(project_id,description) VALUES (:project,'   ')",
            {},
        ),
        "null_requirement": (
            "INSERT INTO project_requirements(project_id,description) VALUES (:project,NULL)",
            {},
        ),
        "negative_order": (
            'INSERT INTO project_requirements(project_id,description,"order") VALUES (:project,:description,-1)',
            {},
        ),
        "review_score": (
            "INSERT INTO project_reviews(submission_id,reviewer_id,score,status_decision) VALUES (:submission,:reviewer,-1,'APPROVED')",
            {},
        ),
        "review_decision": (
            "INSERT INTO project_reviews(submission_id,reviewer_id,score,status_decision) VALUES (:submission,:reviewer,80,'DRAFT')",
            {},
        ),
        "submission_status": (
            "UPDATE project_submissions SET status='INVALID' WHERE id=:submission",
            {},
        ),
        "missing_student": (
            "INSERT INTO project_submissions(project_id,student_id) VALUES (:project,999999)",
            {},
        ),
        "missing_reviewer": (
            "INSERT INTO project_reviews(submission_id,reviewer_id,score,status_decision) VALUES (:submission,999999,80,'APPROVED')",
            {},
        ),
    }
    stmt, _ = statements[kind]
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(
            text(stmt),
            {
                "description": "Bad",
                "track": data.tracks[0].id,
                "project": data.project.id,
                "student": data.users["student"].id,
                "submission": record.id,
                "reviewer": data.users["instructor"].id,
            },
        )


@pytest.mark.parametrize(
    "operation",
    ["get", "list", "update", "reviews", "review", "project_update", "project_remove"],
)
def test_direct_crud_enforces_track_authorization(db_session, data, operation):
    record = make_submission(db_session, data)
    actor = data.users["foreign"]
    with pytest.raises(PermissionError):
        if operation == "get":
            submissions.get(db_session, record.id, actor=actor)
        elif operation == "list":
            submissions.get_multi_by_project(
                db_session, project_id=data.project.id, actor=actor
            )
        elif operation == "update":
            submissions.update(
                db_session,
                submission_id=record.id,
                actor=actor,
                obj_in=ProjectSubmissionUpdate(student_notes="No"),
            )
        elif operation == "reviews":
            submissions.get_reviews(db_session, submission_id=record.id, actor=actor)
        elif operation == "review":
            submissions.create_review(
                db_session,
                submission_id=record.id,
                actor=actor,
                obj_in=ProjectReviewCreate(score=99, feedback="No"),
            )
        elif operation == "project_update":
            projects.update(
                db_session,
                project_id=data.project.id,
                actor=actor,
                obj_in=TrainingProjectUpdate(title="No"),
            )
        else:
            projects.remove(db_session, project_id=data.project.id, actor=actor)


@pytest.mark.parametrize("operation", ["get_multi", "remove"])
def test_generic_crud_cannot_bypass_scope(db_session, operation):
    with pytest.raises(PermissionError):
        getattr(submissions, operation)(db_session)


def test_inactive_actor_denied_in_crud(db_session, data):
    data.users["student"].is_active = False
    with pytest.raises(PermissionError):
        submissions.create(
            db_session,
            project_id=data.project.id,
            actor=data.users["student"],
            obj_in=ProjectSubmissionCreate(),
        )
