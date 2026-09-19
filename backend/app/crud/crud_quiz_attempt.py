from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.crud.base import CRUDBase
from app.models.quiz import Question, Quiz, QuizQuestion
from app.models.quiz_attempt import (
    QuizAnswer,
    QuizAttempt,
    QuizAttemptStatus,
)
from app.schemas.quiz_attempt import QuizAnswerCreate


def _attempt_options_query():
    return (
        selectinload(QuizAttempt.quiz)
        .selectinload(Quiz.question_links)
        .selectinload(QuizQuestion.question)
        .selectinload(Question.options)
    )


def _attempt_answers_query():
    return selectinload(QuizAttempt.answers).selectinload(
        QuizAnswer.selected_option
    )


class CRUDQuizAttempt(CRUDBase[QuizAttempt, QuizAnswerCreate, QuizAnswerCreate]):
    def _get_with_details(
        self,
        db: Session,
        *,
        attempt_id: int,
    ) -> QuizAttempt | None:
        stmt = (
            select(QuizAttempt)
            .options(_attempt_options_query(), _attempt_answers_query())
            .where(QuizAttempt.id == attempt_id)
        )
        return db.execute(stmt).scalar_one_or_none()

    def get(
        self,
        db: Session,
        id: int,
    ) -> QuizAttempt | None:
        return self._get_with_details(db, attempt_id=id)

    def create_for_user(
        self,
        db: Session,
        *,
        quiz_id: int,
        user_id: int,
    ) -> QuizAttempt:
        if db.get(Quiz, quiz_id) is None:
            raise ValueError(f"Quiz {quiz_id} was not found")

        db_obj = QuizAttempt(quiz_id=quiz_id, user_id=user_id)
        db.add(db_obj)
        db.commit()
        return self._get_with_details(db, attempt_id=db_obj.id)  # type: ignore[return-value]

    def get_multi_by_quiz(
        self,
        db: Session,
        *,
        quiz_id: int,
        user_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[QuizAttempt]:
        filters = [QuizAttempt.quiz_id == quiz_id]
        if user_id is not None:
            filters.append(QuizAttempt.user_id == user_id)

        stmt = (
            select(QuizAttempt)
            .options(_attempt_options_query(), _attempt_answers_query())
            .where(*filters)
            .order_by(QuizAttempt.started_at.desc(), QuizAttempt.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()

    def get_multi_by_user(
        self,
        db: Session,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[QuizAttempt]:
        stmt = (
            select(QuizAttempt)
            .options(_attempt_options_query(), _attempt_answers_query())
            .where(QuizAttempt.user_id == user_id)
            .order_by(QuizAttempt.started_at.desc(), QuizAttempt.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()

    def submit(
        self,
        db: Session,
        *,
        db_obj: QuizAttempt,
        answers: Sequence[QuizAnswerCreate],
    ) -> QuizAttempt:
        if db_obj.status != QuizAttemptStatus.IN_PROGRESS.value:
            raise ValueError("Quiz attempt has already been completed")
        if db_obj.answers:
            raise ValueError("Quiz attempt already contains answers")

        questions = {
            link.question_id: link.question for link in db_obj.quiz.question_links
        }
        answer_question_ids = [answer.question_id for answer in answers]
        if len(answer_question_ids) != len(set(answer_question_ids)):
            raise ValueError("Each quiz question may only be answered once")

        correct_points = 0
        total_points = sum(
            max(question.points, 0) for question in questions.values()
        )
        answer_rows: list[QuizAnswer] = []

        for answer in answers:
            question = questions.get(answer.question_id)
            if question is None:
                raise ValueError(
                    f"Question {answer.question_id} does not belong to this quiz"
                )

            selected_option = None
            if answer.selected_option_id is not None:
                selected_option = next(
                    (
                        option
                        for option in question.options
                        if option.id == answer.selected_option_id
                    ),
                    None,
                )
                if selected_option is None:
                    raise ValueError(
                        "Selected option does not belong to the answered question"
                    )

            is_correct = bool(selected_option and selected_option.is_correct)
            if is_correct:
                correct_points += max(question.points, 0)

            answer_rows.append(
                QuizAnswer(
                    attempt_id=db_obj.id,
                    question_id=question.id,
                    selected_option_id=(
                        selected_option.id if selected_option else None
                    ),
                    is_correct=is_correct,
                )
            )

        score = (
            round((correct_points / total_points) * 100, 2)
            if total_points
            else 0.0
        )
        db_obj.answers = answer_rows
        db_obj.score = score
        db_obj.passed = score >= db_obj.quiz.passing_score
        db_obj.status = QuizAttemptStatus.COMPLETED.value
        db_obj.completed_at = datetime.now(UTC)
        db.add(db_obj)
        db.commit()

        return self._get_with_details(db, attempt_id=db_obj.id)  # type: ignore[return-value]


quiz_attempt = CRUDQuizAttempt(QuizAttempt)


def create_quiz_attempt(
    db: Session,
    quiz_id: int,
    user_id: int,
) -> QuizAttempt:
    return quiz_attempt.create_for_user(
        db,
        quiz_id=quiz_id,
        user_id=user_id,
    )


def get_quiz_attempt(db: Session, attempt_id: int) -> QuizAttempt | None:
    return quiz_attempt.get(db, id=attempt_id)


def get_quiz_attempts_by_quiz(
    db: Session,
    quiz_id: int,
    user_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[QuizAttempt]:
    return quiz_attempt.get_multi_by_quiz(
        db,
        quiz_id=quiz_id,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )


def submit_quiz_attempt(
    db: Session,
    db_obj: QuizAttempt,
    answers: Sequence[QuizAnswerCreate],
) -> QuizAttempt:
    return quiz_attempt.submit(db, db_obj=db_obj, answers=answers)
