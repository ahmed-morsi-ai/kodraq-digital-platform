from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models.assignment import Assignment
from app.models.certificate import Certificate
from app.models.graduation import GraduationCheck, GraduationResult, GraduationRule
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.final_project import ProjectReview
from app.models.submission import Submission
from app.services.graduation import (
    calculate_graduation,
    finalize_graduation,
    issue_certificate,
)
from tests.graduation_helpers import seed_graduation


@pytest.fixture
def data(db_session):
    return seed_graduation(db_session)


def calculate(db, data):
    return calculate_graduation(
        db, user_id=data.users["student"].id, track_id=data.tracks[0].id
    )


def gates(calculation):
    return {gate.gate_key: gate for gate in calculation.gate_checks}


def finalize(db, data):
    return finalize_graduation(
        db,
        actor=data.users["instructor"],
        user_id=data.users["student"].id,
        track_id=data.tracks[0].id,
    )


def test_all_gates_pass_without_writing_a_result(db_session, data):
    result = calculate(db_session, data)
    assert result.status == "ELIGIBLE"
    assert result.is_eligible
    assert result.overall_score == 94.5
    assert len(result.gate_checks) == 6
    assert all(gate.passed for gate in result.gate_checks)
    assert db_session.scalar(select(func.count()).select_from(GraduationResult)) == 0
    assert db_session.scalar(select(func.count()).select_from(GraduationRule)) == 0


@pytest.mark.parametrize(
    "failed_gate",
    [
        "enrollment",
        "curriculum_completion",
        "mandatory_assignments",
        "quiz_average",
        "final_project_score",
        "overall_score",
    ],
)
def test_one_failed_gate_fails_entire_graduation_despite_high_overall_score(
    db_session, data, failed_gate
):
    if failed_gate == "enrollment":
        data.enrollment.status = "withdrawn"
    elif failed_gate == "curriculum_completion":
        data.progress.progress_percentage = 99
        data.progress.status = "in_progress"
    elif failed_gate == "mandatory_assignments":
        data.submission.status = "CHANGES_REQUIRED"
        approved = Assignment(
            track_id=data.tracks[0].id,
            title="Completed task",
            description="Task",
            instructions="Task",
            difficulty="beginner",
        )
        db_session.add(approved)
        db_session.flush()
        db_session.add(
            Submission(
                assignment_id=approved.id,
                user_id=data.users["student"].id,
                status="APPROVED",
            )
        )
    elif failed_gate == "quiz_average":
        data.attempt.score = 69.99
    elif failed_gate == "final_project_score":
        data.review.score = 74
    else:
        db_session.add(
            GraduationRule(
                track_id=data.tracks[0].id,
                code="OVERALL_SCORE",
                name="Overall",
                rule_type="THRESHOLD",
                threshold=95,
            )
        )
    db_session.commit()
    result = calculate(db_session, data)
    assert not result.is_eligible
    assert result.status == "NOT_GRADUATED"
    assert not gates(result)[failed_gate].passed
    assert [gate.gate_key for gate in result.gate_checks if not gate.passed] == [
        failed_gate
    ]
    assert result.overall_score > 75
    stored = finalize(db_session, data)
    assert stored.status == "NOT_GRADUATED"
    assert not stored.eligible
    assert stored.finalized_at is None and stored.finalized_by is None
    assert len(stored.checks) == 6


@pytest.mark.parametrize("score,expected", [(69.9999, False), (70, True), (100, True)])
def test_quiz_threshold_is_checked_before_display_rounding(
    db_session, data, score, expected
):
    data.attempt.score = score
    db_session.commit()
    assert gates(calculate(db_session, data))["quiz_average"].passed is expected


@pytest.mark.parametrize(
    "status", ["DRAFT", "SUBMITTED", "UNDER_REVIEW", "CHANGES_REQUIRED", "REJECTED"]
)
def test_unapproved_final_project_never_passes_even_with_old_high_grade(
    db_session, data, status
):
    data.project_submission.status = status
    db_session.commit()
    assert not gates(calculate(db_session, data))["final_project_score"].passed


def test_latest_project_decision_and_grade_are_authoritative(db_session, data):
    db_session.add(
        ProjectReview(
            submission_id=data.project_submission.id,
            reviewer_id=data.users["instructor"].id,
            score=99,
            feedback="Old high score",
            status_decision="APPROVED",
            created_at=datetime(2020, 1, 1, tzinfo=UTC),
        )
    )
    data.review.score = 74
    db_session.commit()
    result = gates(calculate(db_session, data))["final_project_score"]
    assert result.actual_value == 74
    assert not result.passed
    data.review.status_decision = "CHANGES_REQUIRED"
    data.review.score = 99
    db_session.commit()
    assert not gates(calculate(db_session, data))["final_project_score"].passed


@pytest.mark.parametrize(
    "missing", ["project", "submission", "review", "score", "self_review"]
)
def test_missing_or_invalid_final_project_evidence_fails_closed(
    db_session, data, missing
):
    if missing == "project":
        data.project.is_active = False
    elif missing == "submission":
        db_session.delete(data.project_submission)
    elif missing == "review":
        db_session.delete(data.review)
    elif missing == "self_review":
        data.review.reviewer_id = data.users["student"].id
    else:
        data.review.score = None
    db_session.commit()
    assert not gates(calculate(db_session, data))["final_project_score"].passed


def test_project_passing_score_cannot_be_lowered_below_roadmap_floor(db_session, data):
    data.project.passing_score = 60
    data.review.score = 74
    db_session.commit()
    assert (
        gates(calculate(db_session, data))["final_project_score"].required_value == 75
    )
    assert not calculate(db_session, data).is_eligible
    data.project.passing_score = 95
    data.review.score = 90
    db_session.commit()
    assert (
        gates(calculate(db_session, data))["final_project_score"].required_value == 95
    )
    assert not calculate(db_session, data).is_eligible


@pytest.mark.parametrize("scope", ["track", "module", "lesson"])
def test_quizzes_and_assignments_resolve_all_curriculum_scopes(db_session, data, scope):
    for item in [data.quiz, data.assignment]:
        item.track_id = data.tracks[0].id if scope == "track" else None
        item.module_id = data.module.id if scope == "module" else None
        item.lesson_id = data.lesson.id if scope == "lesson" else None
    db_session.commit()
    assert calculate(db_session, data).is_eligible


@pytest.mark.parametrize("record", ["assignment", "quiz"])
def test_inconsistent_curriculum_references_do_not_earn_credit(
    db_session, data, record
):
    getattr(data, record).track_id = data.tracks[1].id
    db_session.commit()
    assert not calculate(db_session, data).is_eligible


def test_quiz_uses_best_completed_attempt_and_requires_every_quiz_to_pass(
    db_session, data
):
    data.attempt.score = 50
    db_session.add_all(
        [
            QuizAttempt(
                quiz_id=data.quiz.id,
                user_id=data.users["student"].id,
                status="IN_PROGRESS",
                score=100,
            ),
            QuizAttempt(
                quiz_id=data.quiz.id,
                user_id=data.users["other"].id,
                status="COMPLETED",
                score=100,
            ),
        ]
    )
    db_session.commit()
    assert not calculate(db_session, data).is_eligible
    db_session.add(
        QuizAttempt(
            quiz_id=data.quiz.id,
            user_id=data.users["student"].id,
            status="COMPLETED",
            score=80,
        )
    )
    data.quiz.passing_score = 85
    db_session.commit()
    gate = gates(calculate(db_session, data))["quiz_average"]
    assert gate.actual_value == 80 and not gate.passed
    data.quiz.passing_score = 80
    second = Quiz(track_id=data.tracks[0].id, title="Unattempted", passing_score=0)
    db_session.add(second)
    db_session.commit()
    assert not calculate(db_session, data).is_eligible
    second.is_active = False
    db_session.commit()
    assert calculate(db_session, data).is_eligible


@pytest.mark.parametrize("score", [None, -1, 101, float("nan"), float("inf")])
def test_invalid_legacy_quiz_scores_never_satisfy_gate(db_session, data, score):
    data.attempt.score = score
    db_session.commit()
    assert not gates(calculate(db_session, data))["quiz_average"].passed


def test_duplicate_assignment_approvals_do_not_inflate_completion(db_session, data):
    db_session.add(
        Submission(
            assignment_id=data.assignment.id,
            user_id=data.users["student"].id,
            status="APPROVED",
        )
    )
    db_session.commit()
    gate = gates(calculate(db_session, data))["mandatory_assignments"]
    assert gate.actual_value == 100 and gate.details["approved"] == 1
    data.assignment.is_mandatory = False
    data.submission.status = "REJECTED"
    db_session.commit()
    assert (
        gates(calculate(db_session, data))["mandatory_assignments"].details["total"]
        == 0
    )


def test_curriculum_percentage_alone_does_not_forge_completion(db_session, data):
    data.progress.status = "in_progress"
    db_session.commit()
    assert not gates(calculate(db_session, data))["curriculum_completion"].passed


def test_foreign_track_work_is_excluded(db_session, data):
    data.assignment.module_id = None
    data.assignment.track_id = data.tracks[1].id
    data.quiz.module_id = None
    data.quiz.track_id = data.tracks[1].id
    data.attempt.score = 0
    data.submission.status = "REJECTED"
    db_session.commit()
    result = gates(calculate(db_session, data))
    assert result["mandatory_assignments"].details["total"] == 0
    assert result["quiz_average"].details["quizzes"] == 0
    assert calculate(db_session, data).is_eligible


@pytest.mark.parametrize(
    "active,mandatory,threshold", [(False, False, 0), (True, False, 0), (True, True, 1)]
)
def test_track_rules_cannot_waive_mandatory_gate_floors(
    db_session, data, active, mandatory, threshold
):
    data.review.score = 74
    db_session.add(
        GraduationRule(
            track_id=data.tracks[0].id,
            code="FINAL_PROJECT",
            name="Project",
            rule_type="THRESHOLD",
            threshold=threshold,
            is_active=active,
            is_mandatory=mandatory,
        )
    )
    db_session.commit()
    assert not calculate(db_session, data).is_eligible


@pytest.mark.parametrize(
    "code,rule_type", [("CRITICAL_FAILURES", "DUMMY"), ("FINAL_PROJECT", "UNSUPPORTED")]
)
def test_unsupported_mandatory_rules_fail_closed(db_session, data, code, rule_type):
    db_session.add(
        GraduationRule(
            track_id=data.tracks[0].id,
            code=code,
            name="Unknown",
            rule_type=rule_type,
            threshold=0,
        )
    )
    db_session.commit()
    assert not calculate(db_session, data).is_eligible


def test_finalization_records_precise_score_all_checks_and_actor_and_is_idempotent(
    db_session, data
):
    result = finalize(db_session, data)
    assert result.status == "GRADUATED" and result.eligible
    assert result.overall_score == 94.5
    assert result.finalized_by == data.users["instructor"].id
    assert result.finalized_at is not None and result.evaluated_at.tzinfo is not None
    assert len(result.checks) == 6 and all(check.passed for check in result.checks)
    assert result.student is data.users["student"]
    assert result in data.tracks[0].graduation_results
    check_ids = [check.id for check in result.checks]
    assert finalize(db_session, data).id == result.id
    assert [check.id for check in result.checks] == check_ids
    assert calculate(db_session, data).status == "GRADUATED"
    certificate = issue_certificate(
        db_session, actor=data.users["admin"], graduation_result_id=result.id
    )
    assert certificate.final_score == 94.5


def test_failed_decision_can_be_reevaluated_after_rework(db_session, data):
    data.review.score = 74
    db_session.commit()
    first = finalize(db_session, data)
    result_id = first.id
    assert first.status == "NOT_GRADUATED"
    data.review.score = 90
    db_session.commit()
    second = finalize(db_session, data)
    assert second.id == result_id and second.status == "GRADUATED"
    assert len(second.checks) == 6
    assert db_session.scalar(select(func.count()).select_from(GraduationCheck)) == 6


def test_live_eligibility_recalculates_after_finalization_without_rewriting_history(
    db_session, data
):
    result = finalize(db_session, data)
    data.progress.status = "in_progress"
    db_session.commit()
    assert calculate(db_session, data).status == "NOT_GRADUATED"
    with pytest.raises(ValueError, match="Current gates fail"):
        finalize(db_session, data)
    assert result.status == "GRADUATED"


def test_failed_commit_rolls_back_result_rules_and_checks(
    db_session, data, monkeypatch
):
    def fail():
        raise RuntimeError("commit failed")

    with monkeypatch.context() as patch:
        patch.setattr(db_session, "commit", fail)
        with pytest.raises(RuntimeError, match="commit failed"):
            finalize(db_session, data)
    assert db_session.scalar(select(func.count()).select_from(GraduationResult)) == 0
    assert db_session.scalar(select(func.count()).select_from(GraduationCheck)) == 0
    assert db_session.scalar(select(func.count()).select_from(GraduationRule)) == 0


@pytest.mark.parametrize(
    "column,value", [("threshold", -1), ("threshold", 101), ("ordering", -1)]
)
def test_rule_database_constraints(db_session, data, column, value):
    with pytest.raises(IntegrityError), db_session.begin_nested():
        rule = GraduationRule(
            track_id=data.tracks[0].id,
            code="TEST",
            name="Test",
            rule_type="THRESHOLD",
            threshold=70,
        )
        setattr(rule, column, value)
        db_session.add(rule)
        db_session.flush()


def test_result_deletion_cascades_checks_and_certificate(db_session, data):
    result = finalize(db_session, data)
    issue_certificate(
        db_session, actor=data.users["admin"], graduation_result_id=result.id
    )
    db_session.delete(result)
    db_session.flush()
    assert db_session.scalar(select(func.count()).select_from(GraduationCheck)) == 0
    assert db_session.scalar(select(func.count()).select_from(Certificate)) == 0


def test_unverified_legacy_result_is_not_reported_as_finalized(db_session, data):
    legacy = GraduationResult(
        student_id=data.users["student"].id,
        track_id=data.tracks[0].id,
        status="GRADUATED",
        eligible=True,
        overall_score=100,
    )
    db_session.add(legacy)
    db_session.commit()
    assert calculate(db_session, data).status == "ELIGIBLE"
    verified = finalize(db_session, data)
    assert (
        verified.id == legacy.id
        and verified.finalized_by == data.users["instructor"].id
    )
    assert len(verified.checks) == 6
    assert calculate(db_session, data).status == "GRADUATED"


@pytest.mark.parametrize(
    "column,value",
    [
        ("status", "FORGED"),
        ("overall_score", -1),
        ("overall_score", 101),
        ("eligible", False),
    ],
)
def test_result_constraints_prevent_invalid_graduation(db_session, data, column, value):
    with pytest.raises(IntegrityError), db_session.begin_nested():
        result = GraduationResult(
            student_id=data.users["student"].id,
            track_id=data.tracks[0].id,
            status="GRADUATED",
            eligible=True,
            overall_score=90,
        )
        setattr(result, column, value)
        db_session.add(result)
        db_session.flush()


def test_one_result_per_student_track(db_session, data):
    finalize(db_session, data)
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            GraduationResult(
                student_id=data.users["student"].id, track_id=data.tracks[0].id
            )
        )
        db_session.flush()


def test_rule_changes_do_not_mutate_finalized_threshold_snapshot(db_session, data):
    result = finalize(db_session, data)
    check = next(item for item in result.checks if item.gate_key == "quiz_average")
    assert check.required_value == 70
    check.rule.threshold = 95
    db_session.commit()
    assert not calculate(db_session, data).is_eligible
    assert check.required_value == 70 and check.passed
