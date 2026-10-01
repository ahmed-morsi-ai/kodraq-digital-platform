from __future__ import annotations

import re
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.session import SessionLocal
from app.models.track import Lesson, Track, TrackModule

TRACK_SLUG = "backend-ai-engineering"
MODULE_TITLE = "Module 1: Advanced Python & Engineering Practices"
LESSON_SPECS = {
    1: {
        "title": "Python Type Hints, Pydantic, and Data Validation",
        "video_url": "https://www.youtube.com/embed/RwH2UzC2rIo",
    },
    2: {
        "title": "Advanced OOP, Dataclasses, and Protocols",
        "video_url": "https://www.youtube.com/embed/Ej_02ICOIgs",
    },
    3: {
        "title": "Async/Await and Concurrency in Python",
        "video_url": "https://www.youtube.com/embed/t5Bo1Je9EmE",
    },
}

IFRAME_PATTERN = re.compile(r"<iframe\b[^>]*>.*?</iframe>", re.IGNORECASE | re.DOTALL)
IFRAME_SRC_PATTERN = re.compile(r"\bsrc\s*=\s*(['\"])(.*?)\1", re.IGNORECASE)
DATA_VALIDATION_HEADING = "**Data Validation Strategies:**"
DATA_VALIDATION_IFRAME = (
    '**Data Validation Strategies:**\n\n'
    '<iframe width="100%" height="450" '
    'src="https://www.youtube.com/embed/7Op2zRkc0Ho" '
    'title="Pydantic Data Validation Strategies" frameborder="0" '
    'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
    'allowfullscreen></iframe>'
)


def remove_duplicate_video_embeds(content: str) -> str:
    seen_sources: set[str] = set()

    def keep_first_embed(match: re.Match[str]) -> str:
        iframe = match.group(0)
        source_match = IFRAME_SRC_PATTERN.search(iframe)
        if source_match is None:
            return iframe
        source = source_match.group(2).strip()
        if source in seen_sources:
            return ""
        seen_sources.add(source)
        return iframe

    return IFRAME_PATTERN.sub(keep_first_embed, content)


def fix_content(ordering: int, content: str | None) -> str:
    updated_content = content or ""
    if ordering == 1:
        heading_index = updated_content.find(DATA_VALIDATION_HEADING)
        if heading_index >= 0:
            updated_content = (
                f"{updated_content[:heading_index].rstrip()}\n\n"
                f"{DATA_VALIDATION_IFRAME}\n"
            )
    return remove_duplicate_video_embeds(updated_content).rstrip() + "\n"


def get_module(session) -> TrackModule:
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
            f"Expected exactly one Module 1 for '{TRACK_SLUG}', found {len(modules)}."
        )
    return modules[0]


def main() -> None:
    with SessionLocal() as session:
        with session.begin():
            module = get_module(session)
            lessons = list(
                session.scalars(
                    select(Lesson)
                    .where(Lesson.module_id == module.id)
                    .order_by(Lesson.ordering, Lesson.id)
                )
            )
            if [lesson.ordering for lesson in lessons] != [1, 2, 3]:
                raise LookupError(
                    "Module 1 must contain exactly one lesson at each ordering 1, 2, and 3."
                )

            for lesson in lessons:
                spec = LESSON_SPECS[lesson.ordering]
                lesson.title = spec["title"]
                lesson.video_url = spec["video_url"]
                lesson.content = fix_content(lesson.ordering, lesson.content)

            session.flush()
            for lesson in lessons:
                sources = [
                    match.group(2).strip()
                    for iframe in IFRAME_PATTERN.findall(lesson.content or "")
                    if (match := IFRAME_SRC_PATTERN.search(iframe)) is not None
                ]
                if (
                    lesson.title != LESSON_SPECS[lesson.ordering]["title"]
                    or lesson.video_url != LESSON_SPECS[lesson.ordering]["video_url"]
                    or len(sources) != len(set(sources))
                ):
                    raise RuntimeError(
                        f"Lesson ordering {lesson.ordering} link verification failed."
                    )

    print("Updated Module 1 lesson order labels, main video URLs, and unique video resources.")


if __name__ == "__main__":
    main()