from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.session import SessionLocal
from app.models.track import Lesson, Track, TrackModule

TRACK_SLUG = "backend-ai-engineering"
MODULE_TITLE = "Module 0: Backend Mindset & Architecture"
LESSON_TITLE = "Introduction to System Design & API Boundaries"
LESSON_DESCRIPTION = (
  "Learn how to turn product requirements into system components and clear API contracts. "
  "Understand functional vs non-functional requirements and layered system architecture."
)
VIDEO_URL = "https://www.youtube.com/embed/m8Icp_Cid5o"
LESSON_QUIZ_DATA = [
  {
    "id": 1,
    "question": "What is the key difference between functional and non-functional requirements?",
    "options": [
      "Functional defines what the system does; non-functional defines qualities like performance and latency.",
      "Functional is only for frontend; non-functional is only for database.",
      "Non-functional requirements are optional and never tested in production.",
      "They are identical concepts in system architecture.",
    ],
    "correct_index": 0,
    "explanation": "Functional requirements describe observable system behavior, such as enrolling a user. Non-functional requirements set measurable operating qualities and constraints, such as a response time below 300 ms at an expected load.",
  },
  {
    "id": 2,
    "question": "Which responsibility belongs primarily to the business-logic layer in a layered backend?",
    "options": [
      "Parse HTTP headers and convert the request body from JSON.",
      "Enforce domain rules, such as checking that a learner is eligible to enroll.",
      "Render buttons and display validation messages in the browser.",
      "Choose the database connection string for each deployment.",
    ],
    "correct_index": 1,
    "explanation": "Business logic coordinates use cases and enforces domain policies. The transport layer handles HTTP parsing and response mapping, while persistence handles database operations and the client presents the interface.",
  },
  {
    "id": 3,
    "question": "What does a clear API boundary provide to a client and the backend team?",
    "options": [
      "A guarantee that the server never needs to validate client input.",
      "A shared database connection that every client can access directly.",
      "A documented contract for operations, inputs, outputs, status codes, and errors.",
      "A requirement to split every feature into a separate microservice.",
    ],
    "correct_index": 2,
    "explanation": "An API boundary defines how clients interact with the system: the operation and resource, request and response shapes, headers, status codes, and predictable errors. The server must still validate input and enforce authorization.",
  },
]

LESSON_CONTENT = """# Introduction to System Design & API Boundaries

System design is the practice of deciding how software components collaborate to meet a set of user and operational needs. A useful design makes responsibilities explicit, protects important constraints, and gives a team room to change the system without making every change risky.

## Section 1: Software Engineer vs. System Architect

A software engineer turns requirements into working, tested software: endpoints, data models, business rules, and operational behavior. A system architect looks across those parts and chooses how responsibilities, data, and dependencies fit together. These are complementary perspectives, not separate ranks or job titles. Engineers make architectural decisions every day, and architects need implementation evidence to validate their designs.

Start by separating two kinds of requirements:

| Requirement type | Question it answers | Example |
| --- | --- | --- |
| Functional | What must the system do? | A learner can enroll in an available course and receive an enrollment identifier. |
| Non-functional | How well or under what constraints must it do it? | Enrollment requests should complete within 300 ms at the 95th percentile under 500 concurrent users. |

Functional requirements describe observable capabilities: create an account, search lessons, or reject enrollment in a full course. Non-functional requirements describe qualities and limits such as latency, throughput, availability, security, accessibility, and cost. They should be measurable where possible. "Fast" is ambiguous; "95% of catalog reads complete within 200 ms at 1,000 requests per second" can guide design and testing.

Scalability is the ability to handle growth while keeping the important service qualities within agreed bounds. For example, if traffic grows from 100 to 2,000 requests per second, a stateless API can add instances behind a load balancer. The database may still become the bottleneck, so the design may also need indexes, connection limits, caching, or read replicas. Adding application servers alone does not guarantee that the whole system scales.

Before choosing technology, write down the behavior, expected load, latency target, failure expectations, and data sensitivity. Those constraints explain why a design is appropriate and make trade-offs visible.

## Section 2: Layered Architecture & Separation of Concerns

Layered architecture separates code by the kind of responsibility it owns. A request can move through these layers, with each layer depending on a clear contract rather than reaching into every other layer's internals.

1. **Client:** A browser, mobile app, or other service initiates an operation. It presents information and sends an HTTP request, but it is not trusted to enforce authorization or protect business data.
2. **Transport:** The API layer receives HTTP, matches a route, parses input, validates its shape, authenticates the caller, and translates application outcomes into status codes, headers, and response bodies. FastAPI route handlers commonly live here.
3. **Business logic:** Application services coordinate use cases and enforce domain rules. For enrollment, this layer can verify that a course is open and that the learner is eligible. It should not need to know how an HTTP request was encoded.
4. **Persistence:** Repositories or data-access code load and store durable state through SQLAlchemy and PostgreSQL. This layer owns query and transaction details, not HTTP response formatting.

For a course enrollment request, the client sends the course identifier; transport validates the request and identifies the caller; business logic checks eligibility and capacity; persistence records the enrollment in a transaction; and transport returns the resulting resource. Each boundary should have a clear input and output.

Separation of concerns improves testability: business rules can be tested without an HTTP server, and route behavior can be tested with a substituted service or database dependency. It also limits change propagation. A database schema change should not require rewriting client-facing response handling if the persistence boundary remains stable. Avoid adding layers that only forward calls without owning a useful policy or abstraction.

## Section 3: The API Contract

An API contract describes the methods, paths, inputs, outputs, headers, and errors a client can rely on. Consider an endpoint that creates a course enrollment:

```http
POST /api/v1/enrollments HTTP/1.1
Content-Type: application/json
Accept: application/json
Authorization: Bearer <access-token>
X-Request-ID: req-7f31
```

Example request body:

```json
{
  "course_id": 42
}
```

On success, the API creates the resource and returns **201 Created**. The `Location` header identifies the new resource; `Content-Type` tells the client how to parse the body. The request ID can be echoed or returned for support and tracing.

```http
HTTP/1.1 201 Created
Content-Type: application/json
Location: /api/v1/enrollments/913
X-Request-ID: req-7f31
```

```json
{
  "id": 913,
  "course_id": 42,
  "student_id": 108,
  "status": "active",
  "created_at": "2026-10-01T12:00:00Z"
}
```

For a syntactically valid JSON request that violates an application rule, such as a missing or non-positive `course_id`, this contract uses **400 Bad Request** and a stable, client-safe error shape. Do not return database traces or secrets in error details.

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json
X-Request-ID: req-7f31
```

```json
{
  "error": {
    "code": "invalid_course_id",
    "message": "course_id must be a positive integer",
    "details": [
      {
        "field": "course_id",
        "issue": "must be greater than zero"
      }
    ],
    "request_id": "req-7f31"
  }
}
```

Choose status codes consistently: `201` means a resource was created, `400` means the request is invalid, `401` means authentication is missing or invalid, `403` means the authenticated caller lacks permission, `404` means the resource is not found, and `500` indicates an unexpected server failure. Document which layer produces each error and keep the response schema predictable.

## Section 4: Modular Monolith vs. Microservices

| Concern | Modular monolith | Microservices |
| --- | --- | --- |
| Deployment | One application is deployed as a unit. | Independently deployable services communicate over defined protocols. |
| Code boundaries | Modules enforce ownership inside one codebase and process. | Service APIs and data ownership enforce boundaries across processes. |
| Data and transactions | A shared database can support straightforward transactions, while modules still need disciplined ownership. | Each service should own its data; cross-service workflows need explicit consistency patterns. |
| Operations | Usually simpler local development, debugging, and monitoring. | Requires distributed tracing, service discovery, network-failure handling, and more deployment automation. |
| Scaling | Scale the application together; isolate hot paths with profiling and targeted techniques. | Scale individual services independently, at the cost of coordination and operational complexity. |
| Good starting point | A small or growing team with related capabilities and evolving requirements. | Teams with mature operational practices and stable boundaries that need independent ownership or scaling. |

Prefer a modular monolith when one deployable application meets current needs. Keep modules cohesive, expose intentional interfaces, and assign ownership of data and rules. Consider extracting a service when there is evidence for independent scaling, deployment, security isolation, or team ownership that outweighs network and operational costs. Microservices do not automatically make a system more scalable or maintainable.

"""


def get_target_lesson(session) -> Lesson:
    lessons = list(
        session.scalars(
            select(Lesson)
            .join(TrackModule, Lesson.module_id == TrackModule.id)
            .join(Track, TrackModule.track_id == Track.id)
            .where(
                Track.slug == TRACK_SLUG,
                TrackModule.title == MODULE_TITLE,
                Lesson.title == LESSON_TITLE,
            )
        )
    )
    if len(lessons) != 1:
        raise LookupError(
            f"Expected exactly one matching lesson, found {len(lessons)}. "
            "Confirm the track and Module 0 have been seeded."
        )
    return lessons[0]


def main() -> None:
    with SessionLocal() as session:
        with session.begin():
            lesson = get_target_lesson(session)
            lesson.description = LESSON_DESCRIPTION
            lesson.content = LESSON_CONTENT
            lesson.video_url = VIDEO_URL
            lesson.quiz_data = LESSON_QUIZ_DATA
            lesson_id = lesson.id

    with SessionLocal() as session:
        persisted_lesson = session.get(Lesson, lesson_id)
        if (
            persisted_lesson is None
            or persisted_lesson.description != LESSON_DESCRIPTION
            or persisted_lesson.content != LESSON_CONTENT
            or persisted_lesson.video_url != VIDEO_URL
            or persisted_lesson.quiz_data != LESSON_QUIZ_DATA
            or "<iframe" in (persisted_lesson.content or "").lower()
        ):
            raise RuntimeError("Lesson content did not persist as expected")
        print(
            f"Updated lesson {persisted_lesson.id}: {persisted_lesson.title} "
            f"({len(LESSON_CONTENT)} characters, embedded video verified)."
        )


if __name__ == "__main__":
    main()