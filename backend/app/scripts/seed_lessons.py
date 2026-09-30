from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.track import Lesson, Track, TrackModule

TRACK_NAME = "Backend & AI Engineering"
LESSONS_BY_MODULE = {
    "Module 00: Backend Mindset": (
        (
            "Understanding Backend Architecture",
            "Explore the responsibilities of a backend service, its data layer, and its API boundary.",
        ),
        (
            "Mapping the Request Lifecycle",
            "Follow a request from the client through routing, validation, business logic, and persistence.",
        ),
    ),
    "Module 01: Advanced Python": (
        (
            "Python Data Models and Type Hints",
            "Use dataclasses, Pydantic models, and type annotations to describe reliable application data.",
        ),
        (
            "Building and Testing FastAPI Endpoints",
            "Create a validated endpoint and test successful responses and invalid input.",
        ),
    ),
    "Module 02: Clean Code & SOLID": (
        (
            "Applying SOLID Principles",
            "Recognize responsibilities and dependencies in a service, then apply the SOLID principles.",
        ),
        (
            "Refactoring for Maintainability",
            "Refactor duplicated logic into focused functions while preserving observable behavior.",
        ),
    ),
    "Module 03: HTTP & Networking": (
        (
            "HTTP Methods and Status Codes",
            "Choose HTTP methods and response status codes that communicate API behavior clearly.",
        ),
        (
            "Designing RESTful API Requests",
            "Model resources, request payloads, headers, and error responses for a REST API.",
        ),
    ),
}


def seed_lessons(session: Session) -> tuple[str, int, list[tuple[str, int]]]:
    track = session.scalar(select(Track).where(Track.name == TRACK_NAME))
    if track is None:
        raise ValueError(f"Track '{TRACK_NAME}' was not found")

    modules = list(
        session.scalars(
            select(TrackModule)
            .where(TrackModule.track_id == track.id)
            .order_by(TrackModule.ordering, TrackModule.id)
        )
    )
    if not modules:
        raise ValueError(f"Track '{TRACK_NAME}' has no modules")

    total_added = 0
    module_results = []
    for module in modules:
        lesson_specs = LESSONS_BY_MODULE.get(
            module.title,
            (
                (
                    f"{module.title}: Understanding the Architecture",
                    f"Learn the core concepts and architecture of {module.title}.",
                ),
                (
                    f"{module.title}: Building a Practical API",
                    f"Apply {module.title} concepts while designing and building a practical API.",
                ),
            ),
        )
        existing_lessons = list(
            session.scalars(
                select(Lesson)
                .where(Lesson.module_id == module.id)
                .order_by(Lesson.ordering, Lesson.id)
            )
        )
        existing_titles = {lesson.title for lesson in existing_lessons}
        next_ordering = max(
            (lesson.ordering for lesson in existing_lessons),
            default=0,
        )
        added_for_module = 0

        for title, content in lesson_specs:
            if title in existing_titles:
                continue
            next_ordering += 1
            session.add(
                Lesson(
                    module_id=module.id,
                    title=title,
                    content=content,
                    ordering=next_ordering,
                )
            )
            existing_titles.add(title)
            added_for_module += 1

        total_added += added_for_module
        module_results.append((module.title, added_for_module))

    return track.name, total_added, module_results


def main() -> None:
    with SessionLocal() as session:
        try:
            track_name, total_added, module_results = seed_lessons(session)
            session.commit()
        except Exception:
            session.rollback()
            raise

    print(f"Seeded lessons for '{track_name}': added {total_added} lessons.")
    for module_title, added_count in module_results:
        print(f"  {module_title}: added {added_count} lessons")


if __name__ == "__main__":
    main()