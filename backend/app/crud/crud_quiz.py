from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased, selectinload

from app.crud.base import CRUDBase
from app.crud.crud_assignment import assignment as curriculum
from app.models.quiz import Question, QuestionOption, Quiz, QuizQuestion
from app.models.track import Lesson, TrackModule
from app.models.track_instructor import TrackInstructor
from app.models.user import User
from app.schemas.quiz import QuestionCreate, QuestionUpdate, QuizCreate, QuizUpdate


def _is_admin(actor: User) -> bool:
    return actor.is_superuser or bool(
        actor.role_rel and actor.role_rel.name.casefold() == "admin"
    )


def _require_manager(actor: User) -> None:
    if not actor.is_active or (
        not _is_admin(actor)
        and (actor.role_rel is None or actor.role_rel.name.casefold() != "instructor")
    ):
        raise PermissionError(
            "Only active admins and instructors can manage quizzes and questions."
        )


def _track_id(db: Session, values: dict) -> int | None:
    return curriculum.resolve_track_id(
        db,
        **{
            field: values.get(field) for field in ("track_id", "module_id", "lesson_id")
        },
    )


def _context(record) -> dict:
    return {
        field: getattr(record, field)
        for field in ("track_id", "module_id", "lesson_id")
    }


def _authorize_track(db: Session, actor: User, track_id: int | None) -> None:
    _require_manager(actor)
    if _is_admin(actor):
        return
    if (
        track_id is None
        or db.scalar(
            select(TrackInstructor.track_id).where(
                TrackInstructor.instructor_id == actor.id,
                TrackInstructor.track_id == track_id,
            )
        )
        is None
    ):
        raise PermissionError("Instructor is not assigned to this curriculum track.")


def _authorize_record(db: Session, actor: User, record) -> None:
    _require_manager(actor)
    if not _is_admin(actor):
        try:
            track_id = _track_id(db, _context(record))
        except (LookupError, ValueError) as error:
            raise PermissionError(
                "The record has inconsistent curriculum references."
            ) from error
        _authorize_track(db, actor, track_id)


def _options(model):
    if model is Question:
        return selectinload(Question.options)
    return (
        selectinload(Quiz.question_links)
        .selectinload(QuizQuestion.question)
        .selectinload(Question.options)
    )


def _commit(db: Session, record):
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(record)
    return record


def _get_many(
    db: Session,
    model,
    *,
    track_id=None,
    module_id=None,
    lesson_id=None,
    skip=0,
    limit=100,
    allowed_tracks=None,
    active_only=False,
):
    if skip < 0 or limit < 0:
        raise ValueError("Pagination values must be non-negative.")
    module, lesson, lesson_module = (
        aliased(TrackModule),
        aliased(Lesson),
        aliased(TrackModule),
    )
    owner = func.coalesce(model.track_id, module.track_id, lesson_module.track_id)
    stmt = (
        select(model)
        .outerjoin(module, model.module_id == module.id)
        .outerjoin(lesson, model.lesson_id == lesson.id)
        .outerjoin(lesson_module, lesson.module_id == lesson_module.id)
        .where(
            or_(model.module_id.is_(None), module.track_id == owner),
            or_(model.lesson_id.is_(None), lesson_module.track_id == owner),
            or_(
                model.module_id.is_(None),
                model.lesson_id.is_(None),
                lesson.module_id == model.module_id,
            ),
        )
    )
    if track_id is not None:
        stmt = stmt.where(owner == track_id)
    if module_id is not None:
        stmt = stmt.where(
            or_(model.module_id == module_id, lesson.module_id == module_id)
        )
    if lesson_id is not None:
        stmt = stmt.where(model.lesson_id == lesson_id)
    if allowed_tracks is not None:
        stmt = stmt.where(owner.in_(allowed_tracks))
    if active_only:
        stmt = stmt.where(Quiz.is_active.is_(True))
    return db.scalars(
        stmt.options(_options(model)).order_by(model.id).offset(skip).limit(limit)
    ).all()


class _CurriculumCRUD(CRUDBase):
    def get(self, db: Session, id: int):
        """Internal read; public question-bank access uses get_for_manager."""
        return db.scalar(
            select(self.model).options(_options(self.model)).where(self.model.id == id)
        )

    def _locked(self, db: Session, record_id: int):
        record = db.scalar(
            select(self.model)
            .where(self.model.id == record_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if record is None:
            raise LookupError(f"{self.model.__name__} not found")
        return record

    def get_for_manager(self, db: Session, *, id: int, actor: User):
        _require_manager(actor)
        record = self.get(db, id=id)
        if record is None:
            raise LookupError(f"{self.model.__name__} not found")
        _authorize_record(db, actor, record)
        if isinstance(record, Quiz):
            for link in record.question_links:
                _authorize_record(db, actor, link.question)
        return record

    def remove(self, db: Session, *, id: int, actor: User):
        _require_manager(actor)
        record = self._locked(db, id)
        _authorize_record(db, actor, record)
        if isinstance(record, Question):
            # Historical scaffolding allowed cross-track mappings. Deleting a
            # question also deletes its links, so authorize those quizzes too.
            for link in record.quiz_questions:
                _authorize_record(db, actor, link.quiz)
        db.delete(record)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        return record


class CRUDQuestion(_CurriculumCRUD):
    def create(self, db: Session, *, obj_in: QuestionCreate, actor: User) -> Question:
        _require_manager(actor)
        data = QuestionCreate.model_validate(obj_in.model_dump()).model_dump()
        _authorize_track(db, actor, _track_id(db, data))
        options = data.pop("options")
        record = Question(
            **data, options=[QuestionOption(**option) for option in options]
        )
        db.add(record)
        return _commit(db, record)

    def update(
        self,
        db: Session,
        *,
        db_obj: Question,
        obj_in: QuestionUpdate | dict,
        actor: User,
    ) -> Question:
        _require_manager(actor)
        changes = QuestionUpdate.model_validate(
            obj_in
            if isinstance(obj_in, dict)
            else obj_in.model_dump(exclude_unset=True)
        ).model_dump(exclude_unset=True)
        record = self._locked(db, db_obj.id)
        _authorize_record(db, actor, record)
        target_track = _track_id(db, _context(record) | changes)
        _authorize_track(db, actor, target_track)
        # Moving a bank question must not silently change the ownership of quizzes using it.
        for link in record.quiz_questions:
            if _track_id(db, _context(link.quiz)) != target_track:
                raise ValueError(
                    "A linked question must remain in the same track as its quizzes."
                )
        options = changes.pop("options", None)
        for field, value in changes.items():
            setattr(record, field, value)
        if options is not None:
            record.options = [QuestionOption(**option) for option in options]
        return _commit(db, record)

    def get_by_context(
        self,
        db: Session,
        *,
        actor: User,
        track_id=None,
        module_id=None,
        lesson_id=None,
        skip=0,
        limit=100,
    ) -> Sequence[Question]:
        _require_manager(actor)
        if any(value is not None for value in (track_id, module_id, lesson_id)):
            _authorize_track(
                db,
                actor,
                _track_id(
                    db,
                    {
                        "track_id": track_id,
                        "module_id": module_id,
                        "lesson_id": lesson_id,
                    },
                ),
            )
        allowed = (
            None
            if _is_admin(actor)
            else db.scalars(
                select(TrackInstructor.track_id).where(
                    TrackInstructor.instructor_id == actor.id
                )
            ).all()
        )
        return _get_many(
            db,
            Question,
            track_id=track_id,
            module_id=module_id,
            lesson_id=lesson_id,
            skip=skip,
            limit=limit,
            allowed_tracks=allowed,
        )

    def get_multi(self, db: Session, *, actor: User, skip=0, limit=100):
        return self.get_by_context(db, actor=actor, skip=skip, limit=limit)

    def get_multi_by_track(
        self, db: Session, *, track_id: int, actor: User, skip=0, limit=100
    ):
        return self.get_by_context(
            db, actor=actor, track_id=track_id, skip=skip, limit=limit
        )

    def get_multi_by_module(
        self, db: Session, *, module_id: int, actor: User, skip=0, limit=100
    ):
        return self.get_by_context(
            db, actor=actor, module_id=module_id, skip=skip, limit=limit
        )

    def get_multi_by_lesson(
        self, db: Session, *, lesson_id: int, actor: User, skip=0, limit=100
    ):
        return self.get_by_context(
            db, actor=actor, lesson_id=lesson_id, skip=skip, limit=limit
        )


class CRUDQuiz(_CurriculumCRUD):
    @staticmethod
    def _validate_links(
        db: Session, links: list[dict], *, track_id: int | None, actor: User
    ) -> None:
        for link in sorted(links, key=lambda item: item["question_id"]):
            record = db.scalar(
                select(Question)
                .where(Question.id == link["question_id"])
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if record is None:
                raise LookupError(f"Question {link['question_id']} not found")
            _authorize_record(db, actor, record)
            if _track_id(db, _context(record)) != track_id:
                raise ValueError(
                    "Quiz questions must belong to the same track as the quiz."
                )

    def create(self, db: Session, *, obj_in: QuizCreate, actor: User) -> Quiz:
        _require_manager(actor)
        data = QuizCreate.model_validate(obj_in.model_dump()).model_dump()
        track_id = _track_id(db, data)
        _authorize_track(db, actor, track_id)
        links = data.pop("questions")
        self._validate_links(db, links, track_id=track_id, actor=actor)
        record = Quiz(**data, question_links=[QuizQuestion(**link) for link in links])
        db.add(record)
        return _commit(db, record)

    def update(
        self, db: Session, *, db_obj: Quiz, obj_in: QuizUpdate | dict, actor: User
    ) -> Quiz:
        _require_manager(actor)
        changes = QuizUpdate.model_validate(
            obj_in
            if isinstance(obj_in, dict)
            else obj_in.model_dump(exclude_unset=True)
        ).model_dump(exclude_unset=True)
        record = self._locked(db, db_obj.id)
        _authorize_record(db, actor, record)
        track_id = _track_id(db, _context(record) | changes)
        _authorize_track(db, actor, track_id)
        links = changes.pop("questions", None)
        effective_links = (
            links
            if links is not None
            else [
                {"question_id": link.question_id, "ordering": link.ordering}
                for link in record.question_links
            ]
        )
        self._validate_links(db, effective_links, track_id=track_id, actor=actor)
        for field, value in changes.items():
            setattr(record, field, value)
        if links is not None:
            existing = {link.question_id: link for link in record.question_links}
            updated = []
            for values in links:
                link = existing.get(values["question_id"])
                if link is None:
                    link = QuizQuestion(**values)
                else:
                    link.ordering = values["ordering"]
                updated.append(link)
            record.question_links = updated
        return _commit(db, record)

    def get_by_context(
        self,
        db: Session,
        *,
        track_id=None,
        module_id=None,
        lesson_id=None,
        skip=0,
        limit=100,
        active_only=False,
        allowed_track_ids=None,
    ) -> Sequence[Quiz]:
        """Internal discovery query; API responses omit correct answers."""
        return _get_many(
            db,
            Quiz,
            track_id=track_id,
            module_id=module_id,
            lesson_id=lesson_id,
            skip=skip,
            limit=limit,
            active_only=active_only,
            allowed_tracks=allowed_track_ids,
        )

    def get_multi(self, db: Session, *, skip=0, limit=100):
        return self.get_by_context(db, skip=skip, limit=limit)

    def get_multi_by_track(self, db: Session, *, track_id: int, skip=0, limit=100):
        return self.get_by_context(db, track_id=track_id, skip=skip, limit=limit)

    def get_multi_by_module(self, db: Session, *, module_id: int, skip=0, limit=100):
        return self.get_by_context(db, module_id=module_id, skip=skip, limit=limit)

    def get_multi_by_lesson(self, db: Session, *, lesson_id: int, skip=0, limit=100):
        return self.get_by_context(db, lesson_id=lesson_id, skip=skip, limit=limit)


question = CRUDQuestion(Question)
quiz = CRUDQuiz(Quiz)
