from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.crud.crud_quiz import question as questions
from app.crud.crud_quiz import quiz as quizzes
from app.models.quiz import Question, QuestionOption, Quiz, QuizQuestion
from app.models.quiz_attempt import QuizAnswer, QuizAttempt
from app.models.role import Role
from app.models.track import Lesson, Track, TrackModule
from app.models.track_instructor import TrackInstructor
from app.models.user import User
from app.schemas.quiz import (
    QuestionCreate,
    QuestionUpdate,
    QuizCreate,
    QuizUpdate,
    StudentQuizResponse,
)


@pytest.fixture
def domain(db_session):
    data = SimpleNamespace(users={})
    for key, role_name in (
        ("admin", "ADMIN"),
        ("instructor", "Instructor"),
        ("student", "student"),
        ("employee", "employee"),
    ):
        data.users[key] = User(
            email=f"quiz-{key}@example.com",
            full_name=key,
            hashed_password="unused",
            role_rel=Role(name=role_name),
            is_active=True,
        )
    data.users["superuser"] = User(
        email="quiz-super@example.com",
        full_name="Superuser",
        hashed_password="unused",
        is_superuser=True,
    )
    data.users["inactive"] = User(
        email="quiz-inactive@example.com",
        full_name="Inactive",
        hashed_password="unused",
        is_superuser=True,
        is_active=False,
    )
    for name in ("a", "b"):
        track = Track(name=f"Quiz foundation {name}", slug=f"quiz-foundation-{name}")
        module = TrackModule(track=track, title=name)
        lesson = Lesson(module=module, title=name)
        db_session.add_all([track, module, lesson])
        setattr(data, name, SimpleNamespace(track=track, module=module, lesson=lesson))
    db_session.add_all(data.users.values())
    db_session.flush()
    db_session.add(
        TrackInstructor(
            track_id=data.a.track.id, instructor_id=data.users["instructor"].id
        )
    )
    db_session.flush()
    return data


def payload(kind, **context):
    if kind == "question":
        return QuestionCreate(
            text="Question",
            question_type="MULTIPLE_CHOICE",
            options=[{"text": "Yes", "is_correct": True}, {"text": "No"}],
            **context,
        )
    return QuizCreate(title="Quiz", passing_score=70, **context)


def crud(kind):
    return questions if kind == "question" else quizzes


def make(db, data, kind="question", **values):
    return crud(kind).create(
        db,
        actor=data.users["admin"],
        obj_in=payload(kind, **({"track_id": data.a.track.id} | values)),
    )


@pytest.mark.parametrize("kind", ["question", "quiz"])
@pytest.mark.parametrize("scope", ["track", "module", "lesson", "full"])
def test_creation_and_bidirectional_curriculum_relationships(
    db_session, domain, kind, scope
):
    contexts = {
        f"{name}_id": getattr(domain.a, name).id
        for name in ("track", "module", "lesson")
        if scope in (name, "full")
    }
    record = crud(kind).create(
        db_session, actor=domain.users["instructor"], obj_in=payload(kind, **contexts)
    )
    for name in ("track", "module", "lesson"):
        if f"{name}_id" in contexts:
            assert getattr(record, name) is getattr(domain.a, name)
            assert record in getattr(
                getattr(domain.a, name),
                "questions" if kind == "question" else "quizzes",
            )
    assert record.created_at.tzinfo is not None
    assert record.updated_at.tzinfo is not None


@pytest.mark.parametrize("kind", ["question", "quiz"])
@pytest.mark.parametrize("operation", ["create", "update", "remove"])
@pytest.mark.parametrize(
    "role", ["admin", "instructor", "superuser", "student", "employee", "inactive"]
)
def test_crud_write_role_boundaries(db_session, domain, kind, operation, role):
    record = make(db_session, domain, kind)
    actor = domain.users[role]

    def act():
        if operation == "create":
            return crud(kind).create(
                db_session,
                actor=actor,
                obj_in=payload(kind, track_id=domain.a.track.id),
            )
        if operation == "update":
            return crud(kind).update(
                db_session,
                actor=actor,
                db_obj=record,
                obj_in={"text" if kind == "question" else "title": "Changed"},
            )
        return crud(kind).remove(db_session, actor=actor, id=record.id)

    if role in {"student", "employee", "inactive"}:
        with pytest.raises(PermissionError):
            act()
        db_session.refresh(record)
        assert getattr(record, "text" if kind == "question" else "title") != "Changed"
    else:
        assert act() is not None


@pytest.mark.parametrize("kind", ["question", "quiz"])
@pytest.mark.parametrize("field", ["track_id", "module_id", "lesson_id"])
def test_missing_curriculum_references(db_session, domain, kind, field):
    with pytest.raises(LookupError):
        crud(kind).create(
            db_session,
            actor=domain.users["admin"],
            obj_in=payload(kind, **{field: 99999999}),
        )


@pytest.mark.parametrize("kind", ["question", "quiz"])
@pytest.mark.parametrize(
    "first,second", [("track", "module"), ("track", "lesson"), ("module", "lesson")]
)
def test_inconsistent_curriculum_references(db_session, domain, kind, first, second):
    with pytest.raises(ValueError):
        crud(kind).create(
            db_session,
            actor=domain.users["admin"],
            obj_in=payload(
                kind,
                **{
                    f"{first}_id": getattr(domain.a, first).id,
                    f"{second}_id": getattr(domain.b, second).id,
                },
            ),
        )


@pytest.mark.parametrize("kind", ["question", "quiz"])
def test_instructor_cannot_move_or_modify_other_tracks_or_unscoped_records(
    db_session, domain, kind
):
    actor = domain.users["instructor"]
    own = make(db_session, domain, kind)
    for context in ({"track_id": domain.b.track.id}, {"track_id": None}):
        with pytest.raises(PermissionError):
            crud(kind).update(db_session, db_obj=own, obj_in=context, actor=actor)
        other = make(db_session, domain, kind, **context)
        for action in (
            lambda: crud(kind).update(db_session, db_obj=other, obj_in={}, actor=actor),
            lambda: crud(kind).remove(db_session, id=other.id, actor=actor),
        ):
            with pytest.raises(PermissionError):
                action()


@pytest.mark.parametrize("kind", ["question", "quiz"])
def test_missing_record_and_negative_pagination(db_session, domain, kind):
    actor = domain.users["admin"]
    assert crud(kind).get(db_session, id=99999999) is None
    with pytest.raises(LookupError):
        crud(kind).remove(db_session, id=99999999, actor=actor)
    with pytest.raises(LookupError):
        crud(kind).get_for_manager(db_session, id=99999999, actor=actor)
    kwargs = {"actor": actor} if kind == "question" else {}
    with pytest.raises(ValueError):
        crud(kind).get_multi(db_session, skip=-1, **kwargs)


@pytest.mark.parametrize(
    "schema,values",
    [
        (QuestionCreate, {"text": " "}),
        (QuestionCreate, {"question_type": ""}),
        (QuestionCreate, {"difficulty": 0}),
        (QuestionCreate, {"difficulty": True}),
        (QuestionCreate, {"difficulty": 1.5}),
        (QuestionCreate, {"points": -1}),
        (QuestionCreate, {"points": 0}),
        (QuestionCreate, {"options": [{"text": ""}]}),
        (QuestionCreate, {"options": [{"text": "A", "is_correct": "yes"}]}),
        (QuestionCreate, {"id": 5}),
        (QuestionCreate, {"module_id": -1}),
        (QuestionUpdate, {"difficulty": None}),
        (QuestionUpdate, {"text": None}),
        (QuestionUpdate, {"points": None}),
        (QuestionUpdate, {"options": None}),
        (QuizCreate, {"title": " "}),
        (QuizCreate, {"title": "x" * 256}),
        (QuizCreate, {"passing_score": -1}),
        (QuizCreate, {"passing_score": 101}),
        (QuizCreate, {"time_limit_minutes": 0}),
        (QuizCreate, {"is_active": "yes"}),
        (QuizCreate, {"questions": [{"question_id": 1}, {"question_id": 1}]}),
        (QuizCreate, {"questions": [{"question_id": 1, "ordering": -1}]}),
        (QuizUpdate, {"title": None}),
        (QuizUpdate, {"passing_score": None}),
        (QuizUpdate, {"is_active": None}),
        (QuizUpdate, {"questions": None}),
        (QuizUpdate, {"questions": [{"question_id": 1}, {"question_id": 1}]}),
        (QuizUpdate, {"id": 5}),
    ],
)
def test_schema_validation(schema, values):
    default = (
        {"text": "Question", "question_type": "MULTIPLE_CHOICE"}
        if schema is QuestionCreate
        else {"title": "Quiz", "passing_score": 70}
        if schema is QuizCreate
        else {}
    )
    with pytest.raises(ValidationError):
        schema.model_validate(default | values)


def test_question_partial_update_replaces_options_and_clears_nullable_fields(
    db_session, domain
):
    record = make(db_session, domain, explanation="Hint", module_id=domain.a.module.id)
    old_options = [option.id for option in record.options]
    questions.update(
        db_session,
        db_obj=record,
        actor=domain.users["instructor"],
        obj_in=QuestionUpdate(
            difficulty=3,
            explanation=None,
            module_id=None,
            options=[{"text": "New", "is_correct": True}],
        ),
    )
    assert record.text == "Question" and record.difficulty == 3
    assert record.explanation is record.module_id is None
    assert [option.text for option in record.options] == ["New"]
    assert all(db_session.get(QuestionOption, id) is None for id in old_options)
    questions.update(
        db_session, db_obj=record, actor=domain.users["admin"], obj_in={"options": []}
    )
    assert record.options == []


def test_quiz_mapping_updates_keep_shared_links_and_stable_order(db_session, domain):
    first, second, third = [make(db_session, domain) for _ in range(3)]
    record = make(
        db_session,
        domain,
        "quiz",
        questions=[
            {"question_id": second.id, "ordering": 0},
            {"question_id": first.id, "ordering": 0},
        ],
    )
    assert [link.question_id for link in record.question_links] == [first.id, second.id]
    quizzes.update(
        db_session,
        db_obj=record,
        actor=domain.users["instructor"],
        obj_in={
            "description": None,
            "time_limit_minutes": None,
            "questions": [
                {"question_id": third.id, "ordering": 1},
                {"question_id": first.id, "ordering": 2},
            ],
        },
    )
    assert [link.question_id for link in record.question_links] == [third.id, first.id]
    assert db_session.get(QuizQuestion, (record.id, second.id)) is None
    assert db_session.get(Question, second.id) is not None
    quizzes.update(
        db_session, db_obj=record, actor=domain.users["admin"], obj_in={"questions": []}
    )
    assert record.question_links == []


def test_link_validation_is_atomic_and_rejects_track_changes(db_session, domain):
    record = make(db_session, domain, "quiz")
    other = make(db_session, domain, track_id=domain.b.track.id)
    for question_id, error in ((99999999, LookupError), (other.id, ValueError)):
        with pytest.raises(error):
            quizzes.update(
                db_session,
                db_obj=record,
                actor=domain.users["admin"],
                obj_in={
                    "title": "Must not persist",
                    "questions": [{"question_id": question_id}],
                },
            )
        db_session.refresh(record)
        assert record.title == "Quiz" and record.question_links == []
    own = make(db_session, domain)
    quizzes.update(
        db_session,
        db_obj=record,
        actor=domain.users["admin"],
        obj_in={"questions": [{"question_id": own.id}]},
    )
    for service, row in ((questions, own), (quizzes, record)):
        with pytest.raises(ValueError):
            service.update(
                db_session,
                db_obj=row,
                actor=domain.users["admin"],
                obj_in={"track_id": domain.b.track.id},
            )


@pytest.mark.parametrize("kind", ["question", "quiz"])
def test_filtering_inherits_track_and_module_before_pagination(
    db_session, domain, kind
):
    first = make(db_session, domain, kind, track_id=None, module_id=domain.a.module.id)
    second = make(db_session, domain, kind, track_id=None, lesson_id=domain.a.lesson.id)
    make(db_session, domain, kind, track_id=domain.b.track.id)
    kwargs = {"actor": domain.users["instructor"]} if kind == "question" else {}
    service = crud(kind)
    assert list(
        service.get_multi_by_track(
            db_session, track_id=domain.a.track.id, skip=1, limit=1, **kwargs
        )
    ) == [second]
    assert list(
        service.get_multi_by_module(db_session, module_id=domain.a.module.id, **kwargs)
    ) == [first, second]
    assert list(
        service.get_multi_by_lesson(db_session, lesson_id=domain.a.lesson.id, **kwargs)
    ) == [second]
    assert list(service.get_multi(db_session, limit=0, **kwargs)) == []


def test_question_bank_scopes_before_pagination_and_denies_students(db_session, domain):
    make(db_session, domain, track_id=domain.b.track.id)
    invalid = Question(
        text="Legacy mismatch",
        question_type="TRUE_FALSE",
        track_id=domain.a.track.id,
        module_id=domain.b.module.id,
    )
    db_session.add(invalid)
    db_session.flush()
    valid = make(db_session, domain)
    assert list(
        questions.get_multi(db_session, actor=domain.users["instructor"], limit=1)
    ) == [valid]
    with pytest.raises(PermissionError):
        questions.get_for_manager(
            db_session, id=invalid.id, actor=domain.users["instructor"]
        )
    for action in (
        lambda: questions.get_multi(db_session, actor=domain.users["student"]),
        lambda: questions.get_for_manager(
            db_session, id=valid.id, actor=domain.users["student"]
        ),
    ):
        with pytest.raises(PermissionError):
            action()


@pytest.mark.parametrize(
    "kind,operation",
    [
        (kind, operation)
        for kind in ("question", "quiz")
        for operation in ("create", "update", "remove")
    ],
)
def test_database_failure_rolls_back_parent_and_children(
    db_session, domain, monkeypatch, kind, operation
):
    child = make(db_session, domain)
    record = make(
        db_session,
        domain,
        kind,
        **({"questions": [{"question_id": child.id}]} if kind == "quiz" else {}),
    )
    model = Question if kind == "question" else Quiz
    count = db_session.scalar(select(func.count()).select_from(model))
    before_options = (
        [option.id for option in record.options] if kind == "question" else None
    )
    with Session(
        bind=db_session.connection(), join_transaction_mode="create_savepoint"
    ) as isolated:
        actor = isolated.get(User, domain.users["admin"].id)
        loaded = isolated.get(model, record.id)

        def fail():
            isolated.flush()
            raise RuntimeError("Failure after flush")

        monkeypatch.setattr(isolated, "commit", fail)
        with pytest.raises(RuntimeError, match="after flush"):
            if operation == "create":
                crud(kind).create(
                    isolated,
                    actor=actor,
                    obj_in=payload(kind, track_id=domain.a.track.id),
                )
            elif operation == "update":
                changes = (
                    {"text": "Changed", "options": []}
                    if kind == "question"
                    else {"title": "Changed", "questions": []}
                )
                crud(kind).update(isolated, actor=actor, db_obj=loaded, obj_in=changes)
            else:
                crud(kind).remove(isolated, actor=actor, id=loaded.id)
    db_session.expire_all()
    assert db_session.scalar(select(func.count()).select_from(model)) == count
    assert getattr(record, "text" if kind == "question" else "title") != "Changed"
    if kind == "question":
        assert [option.id for option in record.options] == before_options
    else:
        assert [link.question_id for link in record.question_links] == [child.id]


@pytest.mark.parametrize(
    "table,field,value",
    [
        ("questions", "difficulty", 0),
        ("questions", "points", -1),
        ("questions", "text", " "),
        ("questions", "question_type", ""),
        ("question_options", "text", ""),
        ("quizzes", "passing_score", 101),
        ("quizzes", "time_limit_minutes", 0),
        ("quizzes", "title", ""),
        ("quiz_questions", "ordering", -1),
    ],
)
def test_database_constraints_reject_invalid_raw_values(
    db_session, domain, table, field, value
):
    question = make(db_session, domain)
    make(db_session, domain, "quiz", questions=[{"question_id": question.id}])
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(
                text(f"UPDATE {table} SET {field}=:value"), {"value": value}
            )


def test_delete_question_cascades_options_links_and_existing_answers(
    db_session, domain
):
    question = make(db_session, domain)
    quiz = make(db_session, domain, "quiz", questions=[{"question_id": question.id}])
    attempt = QuizAttempt(quiz=quiz, user=domain.users["student"])
    answer = QuizAnswer(
        attempt=attempt, question=question, selected_option=question.options[0]
    )
    db_session.add(answer)
    db_session.flush()
    ids = question.id, answer.id, attempt.id, [option.id for option in question.options]
    assert question.quiz_answers == [answer]
    questions.remove(db_session, id=question.id, actor=domain.users["admin"])
    db_session.expire_all()
    assert db_session.get(Question, ids[0]) is None
    assert db_session.get(QuizAnswer, ids[1]) is None
    assert db_session.get(QuizAttempt, ids[2]) is not None
    assert all(db_session.get(QuestionOption, id) is None for id in ids[3])
    assert quiz.question_links == []


def test_delete_quiz_preserves_bank_questions_and_options(db_session, domain):
    question = make(db_session, domain)
    quiz = make(db_session, domain, "quiz", questions=[{"question_id": question.id}])
    quizzes.remove(db_session, id=quiz.id, actor=domain.users["instructor"])
    assert db_session.get(QuizQuestion, (quiz.id, question.id)) is None
    assert db_session.get(Question, question.id) is question
    assert len(question.options) == 2


def test_curriculum_deletion_sets_context_null(db_session, domain):
    question = make(
        db_session, domain, module_id=domain.a.module.id, lesson_id=domain.a.lesson.id
    )
    quiz = make(
        db_session,
        domain,
        "quiz",
        module_id=domain.a.module.id,
        lesson_id=domain.a.lesson.id,
    )
    db_session.delete(domain.a.track)
    db_session.commit()
    for record in (question, quiz):
        db_session.refresh(record)
        assert record.track_id is record.module_id is record.lesson_id is None


def test_student_response_never_exposes_answer_key(db_session, domain):
    question = make(db_session, domain, explanation="Secret explanation")
    quiz = make(db_session, domain, "quiz", questions=[{"question_id": question.id}])
    body = StudentQuizResponse.model_validate(quiz).model_dump()
    assert "is_correct" not in str(body) and "explanation" not in str(body)


@pytest.mark.parametrize("operation", ["read_quiz", "delete_question"])
def test_legacy_cross_track_mappings_cannot_bypass_manager_scope(
    db_session, domain, operation
):
    own_question = make(db_session, domain)
    other_question = make(db_session, domain, track_id=domain.b.track.id)
    own_quiz = make(db_session, domain, "quiz")
    other_quiz = make(db_session, domain, "quiz", track_id=domain.b.track.id)
    db_session.add_all(
        [
            QuizQuestion(quiz=own_quiz, question=other_question),
            QuizQuestion(quiz=other_quiz, question=own_question),
        ]
    )
    db_session.flush()
    actor = domain.users["instructor"]
    with pytest.raises(PermissionError):
        if operation == "read_quiz":
            quizzes.get_for_manager(db_session, id=own_quiz.id, actor=actor)
        else:
            questions.remove(db_session, id=own_question.id, actor=actor)
    assert db_session.get(QuizQuestion, (other_quiz.id, own_question.id)) is not None


def test_existing_question_api_uses_crud_validation_and_inherited_scope(
    client, db_session, domain
):
    headers = {
        "Authorization": f"Bearer {create_access_token(domain.users['instructor'].id)}"
    }
    created = client.post(
        f"/api/v1/tracks/{domain.a.track.id}/questions",
        headers=headers,
        json={
            "text": "Bad context",
            "question_type": "MULTIPLE_CHOICE",
            "lesson_id": domain.b.lesson.id,
        },
    )
    assert created.status_code == 422
    own = make(db_session, domain, track_id=None, module_id=domain.a.module.id)
    assert client.get(f"/api/v1/questions/{own.id}", headers=headers).status_code == 200
    assert (
        client.delete(f"/api/v1/questions/{own.id}", headers=headers).status_code == 204
    )
