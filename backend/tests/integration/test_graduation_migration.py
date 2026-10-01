import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from tests.integration.test_final_project_migration import seed


def seed_graduation_history(connection):
    ids = seed(connection)
    ids["rule"] = connection.scalar(
        text(
            "INSERT INTO graduation_rules(track_id,code,name,rule_type,threshold,created_at,updated_at) VALUES (:track,'FINAL_PROJECT','Final project','THRESHOLD',75,now(),now()) RETURNING id"
        ),
        ids,
    )
    ids["result"] = connection.scalar(
        text(
            "INSERT INTO graduation_results(student_id,track_id,overall_score,status,eligible,evaluated_at,created_at,updated_at) VALUES (:user,:track,91,'GRADUATED',true,'2026-09-28T00:00:00+00:00',now(),now()) RETURNING id"
        ),
        ids,
    )
    ids["check"] = connection.scalar(
        text(
            "INSERT INTO graduation_checks(result_id,rule_id,passed,score,details,created_at,updated_at) VALUES (:result,:rule,true,91,'Keep legacy feedback',now(),now()) RETURNING id"
        ),
        ids,
    )
    ids["evaluation"] = connection.scalar(
        text(
            "INSERT INTO graduation_evaluations(user_id,track_id,overall_score,status,is_eligible) VALUES (:user,:track,88.5,'FAILED_GATES',false) RETURNING id"
        ),
        ids,
    )
    connection.execute(
        text(
            "INSERT INTO graduation_gate_checks(evaluation_id,gate_key,passed,actual_value,required_value,failure_reason) VALUES (:evaluation,'final_project_score',false,74,75,'Keep failure')"
        ),
        ids,
    )
    ids["certificate"] = connection.scalar(
        text(
            "INSERT INTO certificates(student_id,track_id,graduation_result_id,certificate_number,final_score,status,created_at,updated_at) VALUES (:user,:track,:result,'KODRAQ-MIGRATION',91,'ISSUED',now(),now()) RETURNING id"
        ),
        ids,
    )
    return ids


def test_graduation_upgrade_downgrade_reupgrade_preserves_history(migration_database):
    engine, migrate = migration_database
    migrate("upgrade", "f15400000001")
    with engine.begin() as connection:
        ids = seed_graduation_history(connection)
    for iteration in range(2):
        migrate("upgrade", "f15500000001")
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT overall_score, status, eligible, finalized_at IS NOT NULL FROM graduation_results WHERE id=:result"
                ),
                ids,
            ).one()
            assert row == (91, "GRADUATED", True, True)
            row = connection.execute(
                text(
                    "SELECT score,gate_key,required_value,details FROM graduation_checks WHERE id=:check"
                ),
                ids,
            ).one()
            assert row == (
                91,
                "FINAL_PROJECT",
                75,
                {"legacy_text": "Keep legacy feedback"},
            )
            assert (
                connection.scalar(
                    text("SELECT final_score FROM certificates WHERE id=:certificate"),
                    ids,
                )
                == 91
            )
            assert (
                connection.scalar(
                    text(
                        "SELECT overall_score FROM graduation_evaluations_archive WHERE id=:evaluation"
                    ),
                    ids,
                )
                == 88.5
            )
            assert (
                connection.scalar(
                    text(
                        "SELECT failure_reason FROM graduation_gate_checks_archive WHERE evaluation_id=:evaluation"
                    ),
                    ids,
                )
                == "Keep failure"
            )
        inspector = inspect(engine)
        assert "graduation_evaluations" not in inspector.get_table_names()
        assert "graduation_evaluations_archive" in inspector.get_table_names()
        assert inspector.get_foreign_keys("graduation_evaluations_archive") == []
        for statement in [
            "UPDATE graduation_results SET status='FORGED' WHERE id=:result",
            "UPDATE graduation_results SET eligible=false WHERE id=:result",
            "UPDATE graduation_checks SET score=101 WHERE id=:check",
            "UPDATE graduation_rules SET threshold=-1 WHERE id=:rule",
        ]:
            with pytest.raises(IntegrityError), engine.begin() as connection:
                connection.execute(text(statement), ids)
        if iteration == 0:
            migrate("downgrade", "f15400000001")
            with engine.connect() as connection:
                assert (
                    connection.scalar(
                        text("SELECT details FROM graduation_checks WHERE id=:check"),
                        ids,
                    )
                    == "Keep legacy feedback"
                )
                assert (
                    connection.scalar(
                        text(
                            "SELECT overall_score FROM graduation_evaluations WHERE id=:evaluation"
                        ),
                        ids,
                    )
                    == 88.5
                )
            assert len(inspect(engine).get_foreign_keys("graduation_evaluations")) == 2
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM graduation_results WHERE id=:result"), ids)
        assert connection.scalar(text("SELECT count(*) FROM graduation_checks")) == 0
        assert connection.scalar(text("SELECT count(*) FROM certificates")) == 0
    print(
        "Graduation upgrade -> downgrade -> re-upgrade preserved rules, checks, results, certificates, and archived evaluations. Exit code: 0"
    )


def test_downgrade_refuses_to_truncate_fractional_grades(migration_database):
    engine, migrate = migration_database
    migrate("upgrade", "f15400000001")
    with engine.begin() as connection:
        ids = seed_graduation_history(connection)
    migrate("upgrade", "f15500000001")
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE graduation_results SET overall_score=94.5 WHERE id=:result"),
            ids,
        )
    result = migrate("downgrade", "f15400000001", succeeds=False)
    assert "fractional scores exist" in result.stderr
    with engine.connect() as connection:
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version"))
            == "f15500000001"
        )
        assert (
            connection.scalar(
                text("SELECT overall_score FROM graduation_results WHERE id=:result"),
                ids,
            )
            == 94.5
        )


def test_invalid_history_aborts_migration_without_losing_records(migration_database):
    engine, migrate = migration_database
    migrate("upgrade", "f15400000001")
    with engine.begin() as connection:
        ids = seed_graduation_history(connection)
        connection.execute(
            text("UPDATE graduation_results SET eligible=false WHERE id=:result"), ids
        )
    result = migrate("upgrade", "f15500000001", succeeds=False)
    assert "ck_graduation_results_eligible" in result.stderr
    with engine.connect() as connection:
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version"))
            == "f15400000001"
        )
        assert (
            connection.scalar(
                text("SELECT details FROM graduation_checks WHERE id=:check"), ids
            )
            == "Keep legacy feedback"
        )
        assert (
            connection.scalar(
                text(
                    "SELECT overall_score FROM graduation_evaluations WHERE id=:evaluation"
                ),
                ids,
            )
            == 88.5
        )
