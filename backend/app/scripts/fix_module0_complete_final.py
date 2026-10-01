from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.session import SessionLocal
from app.models.track import Lesson, Track, TrackModule
from app.scripts.fix_module0_lessons import (
    LESSON_3_CONTENT,
    LESSON_3_QUIZ_DATA,
)
from app.scripts.seed_lesson_1_content import (
    LESSON_CONTENT as LESSON_1_CONTENT,
    LESSON_QUIZ_DATA as LESSON_1_QUIZ_DATA,
)
from app.scripts.seed_lesson_2_content import (
    LESSON_CONTENT as LESSON_2_CONTENT,
    LESSON_QUIZ_DATA as LESSON_2_QUIZ_DATA,
)

TRACK_SLUG = "backend-ai-engineering"
MODULE_TITLE = "Module 0: Backend Mindset & Architecture"
VIDEO_URL = "https://www.youtube.com/embed/SqsSHF_X6O8"

LESSON_SPECS = (
    {
        "ordering": 1,
        "title": "Introduction to System Design & API Boundaries",
        "description": (
            "Learn how to turn product requirements into system components and clear API contracts. "
            "Understand functional vs non-functional requirements and layered architecture."
        ),
        "content": LESSON_1_CONTENT,
        "quiz_data": LESSON_1_QUIZ_DATA,
    },
    {
        "ordering": 2,
        "title": "The Complete Request/Response Lifecycle",
        "description": (
            "Trace an HTTP request end-to-end: from client DNS and reverse proxy through ASGI server routing, "
            "Pydantic validation, auth guards, DB transactions, and serialized JSON responses."
        ),
        "content": LESSON_2_CONTENT,
        "quiz_data": LESSON_2_QUIZ_DATA,
    },
    {
        "ordering": 3,
        "title": "Understanding Data Flow & Statelessness",
        "description": (
            "Master data movement through backend architectures: differentiate stateful vs. stateless services, "
            "durable persistence, request-scoped memory, and horizontal scaling strategies."
        ),
        "content": LESSON_3_CONTENT,
        "quiz_data": LESSON_3_QUIZ_DATA,
    },
)


def _get_module(session) -> TrackModule:
    modules = list(
        session.scalars(
            select(TrackModule)
            .join(Track, TrackModule.track_id == Track.id)
            .where(
                Track.slug == TRACK_SLUG,
                TrackModule.title == MODULE_TITLE,
            )
        )
    )
    if len(modules) != 1:
        raise LookupError(
            f"Expected exactly one Module 0 for '{TRACK_SLUG}', found {len(modules)}."
        )
    return modules[0]


def _validate_quiz_data(quiz_data: list[dict]) -> None:
    if len(quiz_data) != 3:
        raise ValueError("Each Module 0 lesson must have exactly three quiz questions.")
    for question in quiz_data:
        options = question.get("options")
        correct_index = question.get("correct_index")
        if (
            len(options or []) != 4
            or not isinstance(correct_index, int)
            or not 0 <= correct_index < len(options)
            or not question.get("question")
            or not question.get("explanation")
        ):
            raise ValueError("Quiz questions must have four options and a valid explanation/answer.")


def main() -> None:
    for spec in LESSON_SPECS:
        _validate_quiz_data(spec["quiz_data"])

    updated_lessons: list[tuple[int, str]] = []
    with SessionLocal() as session:
        with session.begin():
            module = _get_module(session)
            lessons = list(
                session.scalars(
                    select(Lesson)
                    .where(Lesson.module_id == module.id)
                    .order_by(Lesson.ordering, Lesson.id)
                )
            )
            if [lesson.ordering for lesson in lessons] != [1, 2, 3]:
                raise LookupError(
                    "Module 0 must contain exactly one lesson at each ordering 1, 2, and 3."
                )

            lesson_by_order = {lesson.ordering: lesson for lesson in lessons}
            for spec in LESSON_SPECS:
                lesson = lesson_by_order[spec["ordering"]]
                lesson.title = spec["title"]
                lesson.description = spec["description"]
                lesson.video_url = VIDEO_URL
                lesson.content = spec["content"]
                lesson.quiz_data = spec["quiz_data"]
                updated_lessons.append((lesson.ordering, lesson.title))

            session.flush()
            for spec in LESSON_SPECS:
                lesson = lesson_by_order[spec["ordering"]]
                if (
                    lesson.title != spec["title"]
                    or lesson.description != spec["description"]
                    or lesson.video_url != VIDEO_URL
                    or lesson.content != spec["content"]
                    or lesson.quiz_data != spec["quiz_data"]
                ):
                    raise RuntimeError(
                        f"Lesson ordering {spec['ordering']} failed transaction verification."
                    )

    for ordering, title in updated_lessons:
        print(f"Updated Module 0 lesson {ordering}: {title}.")


if __name__ == "__main__":
    main()