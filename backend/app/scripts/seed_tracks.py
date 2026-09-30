from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.track import Track, TrackModule

TRACK_NAME = "Backend & AI Engineering"
TRACK_SLUG = "backend-ai-engineering"
MODULES = (
    (1, "Module 00: Backend Mindset"),
    (2, "Module 01: Advanced Python"),
    (3, "Module 02: Clean Code & SOLID"),
    (4, "Module 03: HTTP & Networking"),
)


def seed_tracks(session: Session) -> tuple[Track, int]:
    track = session.scalar(select(Track).where(Track.slug == TRACK_SLUG))
    if track is None:
        track = Track(
            name=TRACK_NAME,
            slug=TRACK_SLUG,
            description="Master Python, FastAPI, and AI RAG systems.",
            is_active=True,
            ordering=1,
            price=1500,
        )
        session.add(track)
        session.flush()
    else:
        track.is_active = True

    existing_titles = set(
        session.scalars(
            select(TrackModule.title).where(TrackModule.track_id == track.id)
        )
    )
    added_modules = 0
    for ordering, title in MODULES:
        if title not in existing_titles:
            session.add(
                TrackModule(
                    track_id=track.id,
                    title=title,
                    ordering=ordering,
                    is_active=True,
                )
            )
            added_modules += 1

    session.flush()
    return track, added_modules


def main() -> None:
    with SessionLocal() as session:
        with session.begin():
            track, added_modules = seed_tracks(session)
            total_modules = len(
                session.scalars(
                    select(TrackModule.id).where(TrackModule.track_id == track.id)
                ).all()
            )
        print(
            f"Seeded track '{track.name}' (id={track.id}); "
            f"added {added_modules} modules, total {total_modules}."
        )


if __name__ == "__main__":
    main()