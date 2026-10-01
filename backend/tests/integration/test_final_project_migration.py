import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError


def seed(connection):
    user = connection.scalar(
        text(
            "INSERT INTO users(email,full_name,hashed_password,is_active,is_superuser) VALUES ('migration@example.com','Migration','unused',true,false) RETURNING id"
        )
    )
    track = connection.scalar(
        text(
            "INSERT INTO tracks(name,slug,is_active,ordering,price,currency,is_premium) VALUES ('Migration','migration',true,0,0,'EGP',false) RETURNING id"
        )
    )
    project = connection.scalar(
        text(
            "INSERT INTO training_projects(track_id,title,passing_score,is_active) VALUES (:track,'Keep project',75,true) RETURNING id"
        ),
        {"track": track},
    )
    requirement = connection.scalar(
        text(
            'INSERT INTO project_requirements(project_id,description,is_mandatory,"order") VALUES (:project,:description,true,2) RETURNING id'
        ),
        {"project": project, "description": "Keep requirement"},
    )
    submission = connection.scalar(
        text(
            "INSERT INTO project_submissions(project_id,student_id,github_url,status,student_notes,submitted_at) VALUES (:project,:user,'https://github.com/owner/repo','APPROVED','Keep notes',now()) RETURNING id"
        ),
        {"project": project, "user": user},
    )
    review = connection.scalar(
        text(
            "INSERT INTO project_reviews(submission_id,reviewer_id,score,feedback,status_decision,rubric_scores) VALUES (:submission,:user,90,'Keep feedback','APPROVED',CAST(:rubric AS JSON)) RETURNING id"
        ),
        {"submission": submission, "user": user, "rubric": '{"legacy":90}'},
    )
    return {
        "user": user,
        "track": track,
        "project": project,
        "requirement": requirement,
        "submission": submission,
        "review": review,
    }


def test_final_project_migration_round_trip(migration_database):
    engine, migrate = migration_database
    migrate("upgrade", "f15300000002")
    with engine.begin() as connection:
        ids = seed(connection)
    for iteration in range(2):
        migrate("upgrade", "f15400000001")
        with engine.connect() as connection:
            assert (
                connection.scalar(
                    text("SELECT title FROM training_projects WHERE id=:project"), ids
                )
                == "Keep project"
            )
            assert (
                connection.scalar(
                    text(
                        "SELECT description FROM project_requirements WHERE id=:requirement"
                    ),
                    ids,
                )
                == "Keep requirement"
            )
            assert (
                connection.scalar(
                    text(
                        "SELECT student_notes FROM project_submissions WHERE id=:submission"
                    ),
                    ids,
                )
                == "Keep notes"
            )
            row = connection.execute(
                text(
                    "SELECT score,feedback,status_decision,rubric_scores FROM project_reviews WHERE id=:review"
                ),
                ids,
            ).one()
            assert row == (90, "Keep feedback", "APPROVED", {"legacy": 90})
        inspector = inspect(engine)
        assert any(
            item["column_names"] == ["track_id"]
            for item in inspector.get_unique_constraints("training_projects")
        )
        assert any(
            item["column_names"] == ["project_id", "student_id"]
            for item in inspector.get_unique_constraints("project_submissions")
        )
        assert (
            next(
                item
                for item in inspector.get_columns("project_requirements")
                if item["name"] == "description"
            )["nullable"]
            is False
        )
        for table in ("project_requirements", "project_submissions", "project_reviews"):
            assert all(
                fk["options"]["ondelete"] == "CASCADE"
                for fk in inspector.get_foreign_keys(table)
            )
        if iteration == 0:
            migrate("downgrade", "f15300000002")
            assert (
                next(
                    item
                    for item in inspect(engine).get_columns("project_requirements")
                    if item["name"] == "description"
                )["nullable"]
                is True
            )
    for statement in (
        "UPDATE training_projects SET passing_score=101 WHERE id=:project",
        "UPDATE project_reviews SET score=-1 WHERE id=:review",
        "INSERT INTO training_projects(track_id,title) VALUES (:track,'Duplicate')",
    ):
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(text(statement), ids)
    with engine.begin() as connection:
        defaults = connection.execute(
            text(
                "INSERT INTO project_requirements(project_id,description) VALUES (:project,'Defaults') RETURNING is_mandatory, \"order\""
            ),
            ids,
        ).one()
        assert defaults == (True, 0)
        connection.execute(text("DELETE FROM training_projects WHERE id=:project"), ids)
        for table in ("project_requirements", "project_submissions", "project_reviews"):
            assert connection.scalar(text(f"SELECT count(*) FROM {table}")) == 0
    print(
        "Final-project upgrade -> downgrade -> re-upgrade preserved records, uniqueness and cascading deletes."
    )


def test_migration_rejects_invalid_history_without_changing_it(migration_database):
    engine, migrate = migration_database
    migrate("upgrade", "f15300000002")
    with engine.begin() as connection:
        ids = seed(connection)
        connection.execute(
            text("UPDATE project_reviews SET score=150 WHERE id=:review"), ids
        )
    failed = migrate("upgrade", "f15400000001", succeeds=False)
    assert "rows violate ck_project_reviews_score" in failed.stderr
    with engine.begin() as connection:
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version"))
            == "f15300000002"
        )
        assert (
            connection.scalar(
                text("SELECT score FROM project_reviews WHERE id=:review"), ids
            )
            == 150
        )
        connection.execute(
            text("UPDATE project_reviews SET score=90 WHERE id=:review"), ids
        )
        connection.execute(
            text(
                "UPDATE project_requirements SET description=NULL WHERE id=:requirement"
            ),
            ids,
        )
    failed = migrate("upgrade", "f15400000001", succeeds=False)
    assert "requirements need non-null descriptions" in failed.stderr
    with engine.begin() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT description FROM project_requirements WHERE id=:requirement"
                ),
                ids,
            )
            is None
        )
        connection.execute(
            text(
                "UPDATE project_requirements SET description='Corrected by operator' WHERE id=:requirement"
            ),
            ids,
        )
    migrate("upgrade", "f15400000001")


def test_historical_submission_alignment_downgrade_restores_user_index(
    migration_database,
):
    engine, migrate = migration_database
    migrate("upgrade", "c4a7e9b2d1f6")
    migrate("upgrade", "d5c8e1a3f7b2")
    migrate("downgrade", "c4a7e9b2d1f6")
    assert any(
        index["name"] == "ix_project_submissions_user_id"
        and index["column_names"] == ["user_id"]
        for index in inspect(engine).get_indexes("project_submissions")
    )
    migrate("upgrade", "d5c8e1a3f7b2")
    assert any(
        index["name"] == "ix_project_submissions_student_id"
        and index["column_names"] == ["student_id"]
        for index in inspect(engine).get_indexes("project_submissions")
    )
