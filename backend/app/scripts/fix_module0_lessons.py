from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.session import SessionLocal
from app.models.track import Lesson, Track, TrackModule
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

LESSON_3_CONTENT = """# Lesson 3: Understanding Data Flow & Statelessness

Backend systems receive, validate, transform, store, and return data across several boundaries. Understanding where each value lives, how long it should live, and which component owns it helps prevent data leaks, stale responses, and scaling bottlenecks.

---

## 1. The Data Journey

Consider a learner updating a profile. The browser sends a JSON request over HTTPS. The API transport layer parses and validates the payload, authentication identifies the caller, and application logic checks which fields that user may change. Persistence writes approved changes to PostgreSQL inside a transaction, after which the API serializes a response for the client.

At every boundary, ask what the data represents, whether it is trusted, who owns it, and whether it must survive a process restart. Validate untrusted input at the edge, keep domain rules in the application layer, and persist durable facts in an authoritative store.

| Data stage | Example | Typical lifetime |
| --- | --- | --- |
| Client input | A profile update request body | Until the request completes |
| Request context | Authenticated user ID and correlation ID | One request |
| Domain state | A learner's saved profile | Durable in the database |
| Derived/cache data | A frequently read course summary | Until expiration or invalidation |
| Response representation | JSON returned to the browser | One response; the client may cache it |

Avoid treating values from the client as authoritative. Derive identity from the verified principal, check ownership on the server, and use database constraints as a final guard for invariants that must remain true under concurrent writes.

---

## 2. Stateful vs. Stateless Services

A stateful service instance relies on local memory or a local filesystem to remember information between requests. If a user's session exists only in one process, a later request routed to another instance may not find that session. Restarting or replacing the instance can also destroy that state.

A stateless application instance does not depend on its own memory to serve the next request. Each request carries or can retrieve the needed identity and context, while durable state is stored in shared systems such as PostgreSQL or a dedicated session store. Statelessness does not mean the product has no state; it means application instances do not own the only copy of state needed across requests.

| Concern | Stateful instance | Stateless application instance |
| --- | --- | --- |
| Session location | Process memory or local disk | Signed token or shared session store |
| Instance replacement | Can lose local state | Durable state remains external to the instance |
| Load balancing | May require sticky sessions | Requests can be routed to any healthy instance |
| Scaling | More coordination and state replication | Add or remove instances more directly |
| Main trade-off | Simple local access, harder failover | Requires shared storage and deliberate consistency rules |

Do not place secrets or authorization decisions in client-controlled state. A signed token protects integrity but does not automatically make its claims current; revocation, role changes, and session expiry may require a shared lookup or short token lifetime.

---

## 3. Request-Scoped Memory and Durable Persistence

Request-scoped memory is useful for temporary work: parsed input, a database session, a correlation ID, or intermediate calculation results. It should be released when the request finishes and should not accidentally be reused by another user's request. In Python, avoid mutable module-level objects for request-specific data and use framework dependencies or context managers to manage resource lifetimes.

Durable data belongs in a system designed to preserve it, such as a relational database with transactions and backups. A database session is a unit of interaction with the database, not the durable store itself. Commit successful changes intentionally, roll back failures, and close the session after its request scope ends.

Background jobs need special care: a job should receive stable identifiers or an explicit payload, then reload authoritative data when it runs. Do not assume that the original HTTP request's memory or database session will still exist.

---

## 4. Horizontal Scaling Strategies

Horizontal scaling adds application instances rather than making one server larger. A load balancer distributes requests across healthy instances. This works best when any instance can process any request without relying on private local state.

Before adding instances, measure the whole request path. CPU saturation may require more application capacity; database connection exhaustion, slow queries, external API latency, or lock contention will not be fixed by adding web workers alone. Set connection pool limits, use query plans and indexes, and apply timeouts so a slow dependency does not consume every request slot.

Keep shared state in the appropriate system: PostgreSQL for durable records, a purpose-built shared store for sessions or short-lived coordination, and object storage for uploaded files. Use health checks and graceful shutdown so instances stop receiving traffic before their resources close.

---

## 5. Cache Consistency & Async Processing

Caches reduce repeated work but introduce a second copy of data that can become stale. Redis is commonly used for short-lived cached values and shared session data. In a cache-aside flow, the application checks Redis, loads a miss from PostgreSQL, and stores the result with a time-to-live (TTL). A write may update PostgreSQL and then invalidate or refresh the corresponding Redis key.

Choose cache keys that include all relevant scope, such as tenant, user permissions, locale, and query parameters. A key that omits authorization context can expose one user's data to another. Decide how much staleness is acceptable, document invalidation behavior, and test updates, expiration, concurrent writes, and cache failures.

For each cached value, be able to answer: what is the source of truth, how long can the value be stale, what invalidates it, and what happens when the cache is unavailable? If those answers are unclear, start without the cache and add it after measuring a real bottleneck.

Move slow or retryable work out of the HTTP request when appropriate. A Celery worker can consume a task from a broker such as Redis, process it asynchronously, and store durable results in PostgreSQL or object storage. Pass stable identifiers rather than request-scoped sessions, make jobs idempotent, and define retry and failure handling so a worker restart does not lose authoritative data.
"""

LESSON_3_QUIZ_DATA = [
    {
        "id": 1,
        "question": "What does statelessness mean for an application instance?",
        "options": [
            "The application never stores user or business data.",
            "The instance does not depend on its own local memory to handle later requests.",
            "Every request must create a new database.",
            "The client is responsible for enforcing all authorization rules.",
        ],
        "correct_index": 1,
        "explanation": "A stateless instance can handle a request without relying on state held only in that process. Durable product state still exists in shared systems such as PostgreSQL, and request context can be supplied or retrieved for each request.",
    },
    {
        "id": 2,
        "question": "Why can a load balancer distribute requests across multiple stateless API containers?",
        "options": [
            "Every container keeps an identical copy of all user sessions in local memory.",
            "An instance does not rely on process-local state to handle a request; shared state lives in an external store.",
            "The load balancer writes database transactions directly.",
            "Requests never need authentication after the first API call.",
        ],
        "correct_index": 1,
        "explanation": "Stateless containers can handle any request because they do not depend on memory held by one particular process. Shared session or domain state is retrieved from an appropriate external store, allowing the load balancer to route to any healthy instance.",
    },
    {
        "id": 3,
        "question": "Where should shared state live when it must survive API container restarts?",
        "options": [
            "Only in a Python module-level variable inside one API container.",
            "In the browser's in-memory cache, as the authoritative server record.",
            "In an external shared system, such as PostgreSQL for durable records and Redis for shared cache or session data.",
            "In the load balancer's local request buffer.",
        ],
        "correct_index": 2,
        "explanation": "Process-local memory disappears when a container restarts and is not shared with other instances. Durable domain records belong in a persistent database such as PostgreSQL; Redis can provide shared sessions or cache data with explicitly managed durability and expiration.",
    },
]

LESSON_SPECS = (
    {
        "ordering": 1,
        "title": "Introduction to System Design & API Boundaries",
        "description": (
            "Learn how to turn product requirements into system components and clear API contracts. "
            "Understand functional vs non-functional requirements and layered architecture."
        ),
        "video_url": "https://www.youtube.com/embed/m8Icp_Cid5o",
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
        "video_url": "https://www.youtube.com/embed/tLzM-QQvvUo",
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
        "video_url": "https://www.youtube.com/embed/z8N3dlsTvhE",
        "content": LESSON_3_CONTENT,
        "quiz_data": LESSON_3_QUIZ_DATA,
    },
)


def get_target_module(session) -> TrackModule:
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
            f"Expected exactly one Module 0 for track '{TRACK_SLUG}', found {len(modules)}."
        )
    return modules[0]


def main() -> None:
    lesson_ids: dict[int, int] = {}
    with SessionLocal() as session:
        with session.begin():
            module = get_target_module(session)
            lessons = {
                lesson.ordering: lesson
                for lesson in session.scalars(
                    select(Lesson).where(Lesson.module_id == module.id)
                )
            }
            missing_orders = [
                spec["ordering"]
                for spec in LESSON_SPECS
                if spec["ordering"] not in lessons
            ]
            if missing_orders:
                raise LookupError(
                    f"Module 0 is missing lesson ordering(s): {missing_orders}."
                )

            for spec in LESSON_SPECS:
                lesson = lessons[spec["ordering"]]
                lesson.title = spec["title"]
                lesson.description = spec["description"]
                lesson.video_url = spec["video_url"]
                lesson.content = spec["content"]
                lesson.quiz_data = spec["quiz_data"]
                lesson_ids[spec["ordering"]] = lesson.id

    with SessionLocal() as session:
        for spec in LESSON_SPECS:
            lesson = session.get(Lesson, lesson_ids[spec["ordering"]])
            if (
                lesson is None
                or lesson.module.ordering != 1
                or lesson.ordering != spec["ordering"]
                or lesson.title != spec["title"]
                or lesson.description != spec["description"]
                or lesson.video_url != spec["video_url"]
                or lesson.content != spec["content"]
                or lesson.quiz_data != spec["quiz_data"]
            ):
                raise RuntimeError(
                    f"Lesson ordering {spec['ordering']} failed persistence verification."
                )
            print(
                f"Updated Module 0 lesson {lesson.ordering}: {lesson.title} "
                f"({len(lesson.quiz_data or [])} quiz questions)."
            )


if __name__ == "__main__":
    main()