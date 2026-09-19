from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.crud.base import CRUDBase
from app.models.quiz import Question, QuestionOption, Quiz, QuizQuestion
from app.models.track import Lesson, TrackModule
from app.schemas.quiz import (
    QuestionCreate,
    QuestionUpdate,
    QuizCreate,
    QuizQuestionCreate,
    QuizUpdate,
)


def _question_options_query():
    return selectinload(Question.options)


def _quiz_questions_query():
    return selectinload(Quiz.question_links).selectinload(
        QuizQuestion.question
    ).selectinload(Question.options)


class CRUDQuestion(CRUDBase[Question, QuestionCreate, QuestionUpdate]):
    def _get_with_options(
        self,
        db: Session,
        *,
        question_id: int,
    ) -> Question | None:
        stmt = (
            select(Question)
            .options(_question_options_query())
            .where(Question.id == question_id)
        )
        return db.execute(stmt).scalar_one_or_none()

    def get(
        self,
        db: Session,
        id: int,
    ) -> Question | None:
        return self._get_with_options(db, question_id=id)

    def create(
        self,
        db: Session,
        *,
        obj_in: QuestionCreate,
    ) -> Question:
        data = obj_in.model_dump()
        options = data.pop("options", [])
        db_obj = Question(**data)
        db_obj.options = [QuestionOption(**option) for option in options]
        db.add(db_obj)
        db.commit()
        return self._get_with_options(db, question_id=db_obj.id)  # type: ignore[return-value]

    def get_multi_by_track(
        self,
        db: Session,
        *,
        track_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Question]:
        return self._get_multi_by_scope(
            db,
            scope_filter=or_(
                Question.track_id == track_id,
                Question.lesson.has(
                    Lesson.module.has(TrackModule.track_id == track_id)
                ),
            ),
            skip=skip,
            limit=limit,
        )

    def get_multi_by_lesson(
        self,
        db: Session,
        *,
        lesson_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Question]:
        return self._get_multi_by_scope(
            db,
            scope_filter=Question.lesson_id == lesson_id,
            skip=skip,
            limit=limit,
        )

    def _get_multi_by_scope(
        self,
        db: Session,
        *,
        scope_filter: Any,
        skip: int,
        limit: int,
    ) -> Sequence[Question]:
        stmt = (
            select(Question)
            .options(_question_options_query())
            .where(scope_filter)
            .order_by(Question.id)
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()

    def update(
        self,
        db: Session,
        *,
        db_obj: Question,
        obj_in: QuestionUpdate,
    ) -> Question:
        update_data = obj_in.model_dump(exclude_unset=True)
        options = update_data.pop("options", None)
        updated = super().update(db, db_obj=db_obj, obj_in=update_data)

        if options is not None:
            updated.options = [QuestionOption(**option) for option in options]
            db.add(updated)
            db.commit()

        return self._get_with_options(db, question_id=updated.id)  # type: ignore[return-value]


class CRUDQuiz(CRUDBase[Quiz, QuizCreate, QuizUpdate]):
    def _get_with_questions(
        self,
        db: Session,
        *,
        quiz_id: int,
    ) -> Quiz | None:
        stmt = (
            select(Quiz)
            .options(_quiz_questions_query())
            .where(Quiz.id == quiz_id)
        )
        return db.execute(stmt).scalar_one_or_none()

    def get(
        self,
        db: Session,
        id: int,
    ) -> Quiz | None:
        return self._get_with_questions(db, quiz_id=id)

    def create(
        self,
        db: Session,
        *,
        obj_in: QuizCreate,
    ) -> Quiz:
        data = obj_in.model_dump()
        question_links = data.pop("questions", [])
        db_obj = Quiz(**data)
        db_obj.question_links = self._build_question_links(db, question_links)
        db.add(db_obj)
        db.commit()
        return self._get_with_questions(db, quiz_id=db_obj.id)  # type: ignore[return-value]

    def update(
        self,
        db: Session,
        *,
        db_obj: Quiz,
        obj_in: QuizUpdate,
    ) -> Quiz:
        update_data = obj_in.model_dump(exclude_unset=True)
        question_links = update_data.pop("questions", None)
        updated = super().update(db, db_obj=db_obj, obj_in=update_data)

        if question_links is not None:
            updated.question_links = self._build_question_links(
                db,
                question_links,
            )
            db.add(updated)
            db.commit()

        return self._get_with_questions(db, quiz_id=updated.id)  # type: ignore[return-value]

    def get_multi_by_track(
        self,
        db: Session,
        *,
        track_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Quiz]:
        return self._get_multi_by_scope(
            db,
            scope_filter=Quiz.track_id == track_id,
            skip=skip,
            limit=limit,
        )

    def get_multi_by_lesson(
        self,
        db: Session,
        *,
        lesson_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Quiz]:
        return self._get_multi_by_scope(
            db,
            scope_filter=Quiz.lesson_id == lesson_id,
            skip=skip,
            limit=limit,
        )

    def _get_multi_by_scope(
        self,
        db: Session,
        *,
        scope_filter: Any,
        skip: int,
        limit: int,
    ) -> Sequence[Quiz]:
        stmt = (
            select(Quiz)
            .options(_quiz_questions_query())
            .where(scope_filter)
            .order_by(Quiz.id)
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()

    @staticmethod
    def _build_question_links(
        db: Session,
        question_links: list[QuizQuestionCreate | dict[str, Any]],
    ) -> list[QuizQuestion]:
        links = []
        for link_data in question_links:
            link = (
                link_data
                if isinstance(link_data, QuizQuestionCreate)
                else QuizQuestionCreate.model_validate(link_data)
            )
            if db.get(Question, link.question_id) is None:
                raise ValueError(f"Question {link.question_id} was not found")
            links.append(
                QuizQuestion(
                    question_id=link.question_id,
                    ordering=link.ordering,
                )
            )
        return links


question = CRUDQuestion(Question)
quiz = CRUDQuiz(Quiz)


def create_question(db: Session, obj_in: QuestionCreate) -> Question:
    return question.create(db, obj_in=obj_in)


def get_question(db: Session, question_id: int) -> Question | None:
    return question.get(db, id=question_id)


def get_questions_by_track(
    db: Session,
    track_id: int,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Question]:
    return question.get_multi_by_track(
        db,
        track_id=track_id,
        skip=skip,
        limit=limit,
    )


def get_questions_by_lesson(
    db: Session,
    lesson_id: int,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Question]:
    return question.get_multi_by_lesson(
        db,
        lesson_id=lesson_id,
        skip=skip,
        limit=limit,
    )


def update_question(
    db: Session,
    db_obj: Question,
    obj_in: QuestionUpdate,
) -> Question:
    return question.update(db, db_obj=db_obj, obj_in=obj_in)


def delete_question(db: Session, question_id: int) -> Question | None:
    return question.remove(db, id=question_id)


def create_quiz(db: Session, obj_in: QuizCreate) -> Quiz:
    return quiz.create(db, obj_in=obj_in)


def get_quiz(db: Session, quiz_id: int) -> Quiz | None:
    return quiz.get(db, id=quiz_id)


def update_quiz(db: Session, db_obj: Quiz, obj_in: QuizUpdate) -> Quiz:
    return quiz.update(db, db_obj=db_obj, obj_in=obj_in)


def delete_quiz(db: Session, quiz_id: int) -> Quiz | None:
    return quiz.remove(db, id=quiz_id)
