from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.crud.base import CRUDBase
from app.models.quiz import Question, Quiz, QuizQuestion
from app.models.quiz_attempt import QuizAnswer, QuizAttempt, QuizAttemptStatus
from app.models.user import User
from app.schemas.quiz_attempt import QuizAnswerCreate, QuizAttemptSubmit
from app.services.quiz_access import (
    is_student,
    require_active,
    require_attempt_read,
    require_quiz,
)
from app.services.quiz_scoring import grade_quiz, validate_quiz


def _options():
    return (
        selectinload(QuizAttempt.quiz)
        .selectinload(Quiz.question_links)
        .selectinload(QuizQuestion.question)
        .selectinload(Question.options),
        selectinload(QuizAttempt.answers).selectinload(QuizAnswer.selected_option),
    )


class CRUDQuizAttempt(CRUDBase[QuizAttempt, QuizAnswerCreate, QuizAttemptSubmit]):
    def get(self, db: Session, id: int) -> QuizAttempt | None:
        """Internal read; endpoints use get_for_user for actor authorization."""
        return db.scalar(
            select(QuizAttempt).options(*_options()).where(QuizAttempt.id == id)
        )

    def get_for_user(self, db: Session, *, attempt_id: int, actor: User) -> QuizAttempt:
        require_active(actor)
        attempt = self.get(db, attempt_id)
        if attempt is None:
            raise LookupError("Quiz attempt not found")
        require_attempt_read(db, actor, attempt)
        return attempt

    @staticmethod
    def _commit(db: Session, attempt: QuizAttempt) -> QuizAttempt:
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        db.refresh(attempt)
        return attempt

    @staticmethod
    def _quiz(db: Session, quiz_id: int, *, lock=False) -> Quiz:
        stmt = select(Quiz).where(Quiz.id == quiz_id)
        if lock:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        quiz = db.scalar(stmt)
        if quiz is None:
            raise LookupError("Quiz not found")
        return quiz

    @staticmethod
    def _lock_questions(db: Session, quiz: Quiz) -> None:
        # Same quiz -> question lock order as authoring CRUD; options are changed
        # only while their parent question is locked by that CRUD layer.
        ids = [link.question_id for link in quiz.question_links]
        db.scalars(
            select(Question)
            .where(Question.id.in_(ids))
            .order_by(Question.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).all()

    def create_for_user(self, db: Session, *, quiz_id: int, actor: User) -> QuizAttempt:
        require_active(actor)
        if not is_student(actor):
            raise PermissionError("Only students can start quiz attempts.")
        quiz = self._quiz(db, quiz_id, lock=True)
        if not quiz.is_active:
            raise LookupError("Quiz not found")
        require_quiz(db, actor, quiz)
        self._lock_questions(db, quiz)
        validate_quiz(quiz)
        # Serializing on the quiz makes a retried start request resume the same
        # active attempt instead of issuing parallel papers to the same student.
        existing = db.scalar(
            select(QuizAttempt)
            .where(
                QuizAttempt.quiz_id == quiz_id,
                QuizAttempt.user_id == actor.id,
                QuizAttempt.status == "IN_PROGRESS",
            )
            .order_by(QuizAttempt.id.desc())
            .with_for_update()
        )
        if existing is not None:
            db.commit()
            return existing
        started = datetime.now(UTC)
        attempt = QuizAttempt(
            quiz_id=quiz_id,
            user_id=actor.id,
            started_at=started,
            passing_score=quiz.passing_score,
            deadline_at=started + timedelta(minutes=quiz.time_limit_minutes)
            if quiz.time_limit_minutes is not None
            else None,
        )
        db.add(attempt)
        return self._commit(db, attempt)

    def create(self, db: Session, *, quiz_id: int, actor: User) -> QuizAttempt:
        return self.create_for_user(db, quiz_id=quiz_id, actor=actor)

    def update(self, *args, **kwargs):
        raise PermissionError(
            "Attempts can only be updated through server-side submission scoring."
        )

    def remove(self, *args, **kwargs):
        raise PermissionError(
            "Individual quiz attempts cannot be deleted through CRUD."
        )

    def get_multi(self, *args, **kwargs):
        raise PermissionError("Use the authorized quiz attempt listing.")

    def get_multi_by_quiz(
        self, db: Session, *, quiz_id: int, actor: User, skip=0, limit=100
    ):
        require_active(actor)
        if skip < 0 or limit < 0:
            raise ValueError("Pagination values must be non-negative.")
        quiz = self._quiz(db, quiz_id)
        stmt = select(QuizAttempt).where(QuizAttempt.quiz_id == quiz_id)
        if is_student(actor):
            stmt = stmt.where(QuizAttempt.user_id == actor.id)
        else:
            # The shared read policy always checks instructor membership, even
            # when an instructor owns an older attempt made as a student.
            from app.crud.crud_quiz import quiz as quizzes

            quizzes.get_for_manager(db, id=quiz.id, actor=actor)
        return db.scalars(
            stmt.options(*_options())
            .order_by(QuizAttempt.started_at.desc(), QuizAttempt.id.desc())
            .offset(skip)
            .limit(limit)
        ).all()

    def submit(
        self, db: Session, *, attempt_id: int, actor: User, obj_in: QuizAttemptSubmit
    ) -> QuizAttempt:
        require_active(actor)
        if not is_student(actor):
            raise PermissionError("Only the student who owns an attempt can submit it.")
        payload = QuizAttemptSubmit.model_validate(obj_in.model_dump())
        original = self.get_for_user(db, attempt_id=attempt_id, actor=actor)
        quiz = self._quiz(db, original.quiz_id, lock=True)
        attempt = db.scalar(
            select(QuizAttempt)
            .where(QuizAttempt.id == attempt_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if attempt is None:
            raise LookupError("Quiz attempt not found")
        if attempt.user_id != actor.id:
            raise PermissionError("Only the attempt owner can submit answers.")
        if attempt.status != QuizAttemptStatus.IN_PROGRESS.value:
            raise ValueError("Quiz attempt has already been completed.")
        require_quiz(db, actor, quiz)
        if not quiz.is_active:
            raise LookupError("Quiz not found")
        self._lock_questions(db, quiz)
        now = datetime.now(UTC)
        expired = attempt.deadline_at is not None and now >= attempt.deadline_at
        flagged = attempt.is_flagged or payload.is_flagged or expired
        reason = None
        if flagged:
            reason = (
                attempt.flag_reason
                or (payload.flag_reason or "").strip()
                or "ANTI_CHEAT_VIOLATION"
            )
        if expired:
            reason = "TIME_LIMIT_EXCEEDED"
        grade = grade_quiz(
            quiz,
            [] if expired else payload.answers,
            passing_score=attempt.passing_score
            if attempt.passing_score is not None
            else quiz.passing_score,
            flagged=flagged,
        )
        attempt.answers = [QuizAnswer(**row) for row in grade.pop("rows")]
        attempt.score, attempt.passed = grade["score"], grade["passed"]
        attempt.status = QuizAttemptStatus.COMPLETED.value
        attempt.completed_at, attempt.is_flagged, attempt.flag_reason = (
            now,
            flagged,
            reason,
        )
        attempt.result_snapshot = {
            **grade,
            "attempt_id": attempt.id,
            "quiz_id": quiz.id,
            "time_taken_seconds": max((now - attempt.started_at).total_seconds(), 0),
            "is_flagged": flagged,
            "flag_reason": reason,
        }
        self._commit(db, attempt)
        if expired:
            raise ValueError("Quiz attempt has expired. Its result is available.")
        return attempt

    def build_result(self, db: Session, *, attempt_id: int, actor: User) -> dict:
        attempt = self.get_for_user(db, attempt_id=attempt_id, actor=actor)
        if (
            attempt.status != QuizAttemptStatus.COMPLETED.value
            or attempt.completed_at is None
        ):
            raise ValueError(
                "Quiz attempt results are available only after completion."
            )
        if attempt.result_snapshot is not None:
            return attempt.result_snapshot
        # Legacy completed attempts predate snapshots. Freeze the available
        # historical details on first authorized read, preserving the saved grade.
        quiz = self._quiz(db, attempt.quiz_id, lock=True)
        attempt = db.scalar(
            select(QuizAttempt)
            .where(QuizAttempt.id == attempt_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if attempt.result_snapshot is None:
            answers = {answer.question_id: answer for answer in attempt.answers}
            results = []
            earned = 0
            for link in quiz.question_links:
                question = link.question
                answer = answers.get(question.id)
                selected = answer.selected_option if answer else None
                correct = [option for option in question.options if option.is_correct]
                if answer and answer.is_correct:
                    earned += question.points
                results.append(
                    {
                        "question_id": question.id,
                        "question_text": question.text,
                        "points": question.points,
                        "selected_option_id": selected.id if selected else None,
                        "selected_option_text": selected.text if selected else None,
                        "correct_option_ids": [option.id for option in correct],
                        "correct_option_texts": [option.text for option in correct],
                        "is_correct": bool(answer and answer.is_correct),
                    }
                )
            attempt.result_snapshot = {
                "attempt_id": attempt.id,
                "quiz_id": quiz.id,
                "score": float(attempt.score or 0),
                "percentage": float(attempt.score or 0),
                "max_score": sum(link.question.points for link in quiz.question_links),
                "earned_points": 0 if attempt.is_flagged else earned,
                "passed": attempt.passed,
                "time_taken_seconds": max(
                    (attempt.completed_at - attempt.started_at).total_seconds(), 0
                ),
                "is_flagged": attempt.is_flagged,
                "flag_reason": attempt.flag_reason,
                "questions": results,
            }
            self._commit(db, attempt)
        return attempt.result_snapshot


quiz_attempt = CRUDQuizAttempt(QuizAttempt)
