from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.session import SessionLocal
from app.models.track import Lesson, Track, TrackModule

TRACK_SLUG = "backend-ai-engineering"
MODULE_TITLE = "Module 0: Backend Mindset & Architecture"
VIDEO_URLS = {
    1: "https://www.youtube.com/embed/C842vFY5kRo",
    2: "https://www.youtube.com/embed/csMhnJMhCsE",
    3: "https://www.youtube.com/embed/20tpk8A_xa0",
}
RESOURCE_MARKER = "### 🎥 Additional Video Resources"
ADDITIONAL_VIDEO_RESOURCES = """---
### 🎥 Additional Video Resources

**1. What is Dataflow? (Google Cloud)**

<iframe width="100%" height="450" src="https://www.youtube.com/embed/KalJ0VuEM7s" title="What is Dataflow? (Google Cloud)" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

**2. Data Flow Diagram (DFD) Explanation:**

<iframe width="100%" height="450" src="https://www.youtube.com/embed/vGd_ATD4FnI" title="Data Flow Diagram (DFD) Explanation" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>"""


def get_module0(session) -> TrackModule:
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


def append_video_resources(content: str | None) -> str:
    existing_content = (content or "").rstrip()
    marker_index = existing_content.find(RESOURCE_MARKER)
    if marker_index >= 0:
        existing_content = existing_content[:marker_index].rstrip()
    return f"{existing_content}\n\n{ADDITIONAL_VIDEO_RESOURCES}\n"


def main() -> None:
    with SessionLocal() as session:
        with session.begin():
            module = get_module0(session)
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

            for lesson in lessons:
                lesson.video_url = VIDEO_URLS[lesson.ordering]
            lesson_three = lessons[2]
            lesson_three.content = append_video_resources(lesson_three.content)
            session.flush()

            for lesson in lessons:
                if lesson.video_url != VIDEO_URLS[lesson.ordering]:
                    raise RuntimeError(
                        f"Lesson ordering {lesson.ordering} video URL failed verification."
                    )
            if (
                not lesson_three.content
                or lesson_three.content.count("<iframe") != 2
                or lesson_three.content.count(RESOURCE_MARKER) != 1
            ):
                raise RuntimeError("Lesson 3 additional video embeds failed verification.")

    print("Updated Module 0 lesson video URLs and Lesson 3 video resources.")


if __name__ == "__main__":
    main()