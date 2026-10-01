from datetime import UTC, datetime

from sqlalchemy import select

from app.models.assignment import Assignment
from app.models.enrollment import Enrollment, StudentProgress
from app.models.final_project import ProjectReview
from app.models.project_submission import ProjectSubmission
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.submission import Submission
from app.models.track import Lesson, TrackModule
from tests.final_project_helpers import seed_final_projects


def seed_graduation(db):
    data = seed_final_projects(db)
    student = data.users["student"]
    data.enrollment = db.scalar(
        select(Enrollment).where(
            Enrollment.user_id == student.id, Enrollment.track_id == data.tracks[0].id
        )
    )
    data.module = TrackModule(track_id=data.tracks[0].id, title="Module", ordering=0)
    data.lesson = Lesson(module=data.module, title="Lesson", ordering=0)
    db.add_all([data.module, data.lesson])
    db.flush()
    data.progress = StudentProgress(
        enrollment_id=data.enrollment.id,
        lesson_id=data.lesson.id,
        status="completed",
        progress_percentage=100,
    )
    data.assignment = Assignment(
        module_id=data.module.id,
        title="Assignment",
        description="Description",
        instructions="Instructions",
        difficulty="beginner",
        is_mandatory=True,
    )
    data.quiz = Quiz(module_id=data.module.id, title="Quiz", passing_score=70)
    db.add_all([data.progress, data.assignment, data.quiz])
    db.flush()
    data.submission = Submission(
        assignment_id=data.assignment.id,
        user_id=student.id,
        status="APPROVED",
        grade=90,
    )
    data.attempt = QuizAttempt(
        quiz_id=data.quiz.id,
        user_id=student.id,
        status="COMPLETED",
        score=88,
        passed=True,
        completed_at=datetime.now(UTC),
    )
    data.project_submission = ProjectSubmission(
        project_id=data.project.id,
        student_id=student.id,
        status="APPROVED",
        github_url="https://github.com/student/final",
        submitted_at=datetime.now(UTC),
    )
    db.add_all([data.submission, data.attempt, data.project_submission])
    db.flush()
    data.review = ProjectReview(
        submission_id=data.project_submission.id,
        reviewer_id=data.users["instructor"].id,
        score=90,
        feedback="Approved",
        status_decision="APPROVED",
    )
    db.add(data.review)
    db.commit()
    return data
