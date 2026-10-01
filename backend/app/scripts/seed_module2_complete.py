from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.session import SessionLocal
from app.models.track import Lesson, Track, TrackModule

TRACK_SLUG = "backend-ai-engineering"
MODULE_TITLE = "Module 2: FastAPI and Production API Design"

LESSON_SPECS = (
    {
        "ordering": 1,
        "title": "Setting up FastAPI and Project Structure",
        "description": "Learn how to structure a production-grade FastAPI application, configure environment settings, and bootstrap modular project architecture.",
        "video_url": "https://www.youtube.com/embed/SR5NYCdzKkc",
        "content": """# Setting up FastAPI and Project Structure

FastAPI is a Python framework for building typed HTTP APIs. A production service needs more than routes: it needs clear ownership boundaries, validated configuration, predictable startup and shutdown, and a structure that remains understandable as features grow.

## 1. Why FastAPI?

FastAPI builds on Starlette for ASGI web handling and uses Pydantic for parsing and validating data. It supports asynchronous route handlers when the full I/O path is async, while still allowing ordinary synchronous functions for blocking libraries. Type annotations feed request validation and generate an OpenAPI contract automatically.

The built-in documentation pages expose the generated contract through Swagger UI and ReDoc. This helps client developers inspect paths, schemas, and responses, but documentation is only as accurate as the schemas and route behavior behind it. Always test the actual HTTP contract.

Use `async def` when awaiting non-blocking I/O, such as an async HTTP client. A synchronous database session or CPU-heavy operation inside an async function can block the event loop; choose a matching execution strategy rather than adding `async` mechanically.

## 2. Production Project Architecture

Organize code by responsibility so transport, validation, domain behavior, and persistence do not become one large route module:

```text
app/
  api/          # routers and HTTP dependencies
  core/         # settings, security, logging
  schemas/      # request and response contracts
  models/       # SQLAlchemy persistence mappings
  crud/         # database access operations
  services/     # application use cases and domain coordination
  main.py       # application creation and router registration
```

An API route should parse transport input, invoke a focused service or CRUD operation, and translate the result to an HTTP response. Keep database query details out of schema classes and avoid letting every route import another route's internals. A modular monolith can still have strict boundaries without the operational overhead of premature microservices.

Group endpoints by resource or capability, use consistent response schemas, and centralize reusable dependencies such as authenticated-user and database-session providers. Add focused tests around service behavior and request/response integration.

## 3. Environment Configuration

Configuration differs by environment: local development, tests, staging, and production may use different database URLs, signing keys, and provider credentials. Read settings from environment variables and a local `.env` file for development; keep real secrets out of source control and container images.

Pydantic Settings can validate values at startup so a missing or malformed required setting fails clearly instead of surfacing during a request:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

Use distinct development and production settings, set safe defaults only for non-secret values, and restrict secret access to the service that needs it. Never log credentials or return them from a configuration endpoint.

## 4. Application Lifecycle and Deployment Readiness

Create the FastAPI application in a predictable module and register routers centrally. Initialize long-lived clients through lifespan management, close them during shutdown, and keep per-request database sessions in dependencies. Add health checks that distinguish process liveness from readiness to serve traffic.

Before deployment, verify configuration validation, OpenAPI generation, structured logs, error handling, startup behavior, and tests using the same settings model as production. A well-structured service is easier to extend because each layer has a clear job.
""",
        "quiz_data": [
            {
                "id": 1,
                "question": "Which technologies form the core foundation of FastAPI's HTTP handling and data validation?",
                "options": [
                    "Django templates and Marshmallow only.",
                    "Starlette for ASGI web handling and Pydantic for data validation.",
                    "Flask's WSGI server and SQLAlchemy migrations.",
                    "React Router and browser form validation.",
                ],
                "correct_index": 1,
                "explanation": "FastAPI is built on Starlette for ASGI request handling and uses Pydantic to parse and validate typed data. It also derives OpenAPI documentation from route and schema declarations.",
            },
            {
                "id": 2,
                "question": "What is the purpose of separating routers, schemas, models, CRUD, and core settings into modules?",
                "options": [
                    "To ensure every route owns a separate database server.",
                    "To separate transport, contracts, persistence, database operations, and cross-cutting configuration by responsibility.",
                    "To make Python skip type checking.",
                    "To replace the need for integration tests.",
                ],
                "correct_index": 1,
                "explanation": "A modular structure gives each layer a clear responsibility and reduces coupling. It makes the service easier to test and evolve without requiring separate deployable services for every feature.",
            },
            {
                "id": 3,
                "question": "Where should production secrets such as signing keys and database credentials be stored?",
                "options": [
                    "Committed directly into the repository's Python settings file.",
                    "Returned to clients through an application settings endpoint.",
                    "Injected through environment configuration or a secret manager, outside source control.",
                    "Hard-coded as defaults in every route module.",
                ],
                "correct_index": 2,
                "explanation": "Secrets should be injected at runtime from environment configuration or a secret manager and should never be committed or returned to clients. Pydantic Settings can validate required configuration at startup.",
            },
        ],
    },
    {
        "ordering": 2,
        "title": "Request Validation, Query Params, and Path Operations",
        "description": "Master FastAPI request handling, robust query and path parameters validation using Pydantic, and RESTful path operations.",
        "video_url": "https://www.youtube.com/embed/6uN6GxMwzVI",
        "content": """# Request Validation, Query Params, and Path Operations

FastAPI turns Python function signatures into an HTTP contract. Path parameters identify a resource, query parameters refine a collection request, and request bodies carry structured data for create or update operations. Explicit validation makes the API predictable for clients and safer for the service.

## 1. Path & Query Parameters

Path parameters identify a resource, such as `/courses/42`. Query parameters filter, sort, or paginate a collection, such as `/courses?skip=0&limit=25`. Annotate values with Python types, define sensible defaults, and constrain values with `Path()` and `Query()`:

```python
from typing import Annotated
from fastapi import Path, Query

@router.get("/courses/{course_id}")
def read_course(
    course_id: Annotated[int, Path(gt=0)],
    include_lessons: bool = False,
):
    ...

@router.get("/courses")
def list_courses(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = None,
):
    ...
```

Use `Body()` when you need to disambiguate or document a request body explicitly. Reject unreasonable pagination limits, normalize query values deliberately, and never interpolate raw user input into SQL strings.

## 2. Request Body & Pydantic Schemas

Define Pydantic models for nested JSON payloads. Field types, defaults, and constraints describe which values are accepted; nested schemas make complex requests easier to validate and document.

```python
from pydantic import BaseModel, Field

class LessonCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    duration_minutes: int = Field(gt=0, le=600)

class CourseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    lessons: list[LessonCreate] = Field(default_factory=list)
```

FastAPI parses the incoming JSON and validates it before calling the route handler. Invalid types, missing required fields, or failed constraints produce a structured `422 Unprocessable Entity` response. Validation at the HTTP boundary does not replace business rules that require a database lookup, such as checking whether a referenced instructor exists.

## 3. Status Codes & Response Models

Set status codes to communicate the result explicitly. A successful resource creation commonly returns `201 Created`; reads return `200 OK`; invalid input is rejected with a client error. Use `status.HTTP_201_CREATED` instead of unexplained numeric literals.

```python
from fastapi import status

@router.post(
    "/courses",
    response_model=CourseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_course(payload: CourseCreate):
    ...
```

A response model documents and filters outgoing data. Return a public schema rather than a persistence object containing password hashes or internal-only fields. Test success and failure responses, including status, headers, and response shape.

## 4. Designing Predictable Operations

Use nouns for resources, HTTP methods consistently, and stable response schemas. Keep routes thin: validate request data, call application behavior, and translate known outcomes into meaningful status codes. Add tests for boundary values such as missing query parameters, zero or negative IDs, oversized page limits, nested invalid data, and nonexistent resources.

---
### Additional Video Resources

**Advanced Query & Path Validation:**
<iframe width="100%" height="450" src="https://www.youtube.com/embed/tG7x9Ty1ocg" title="Advanced Query and Path Validation" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

**Request Body Deep Dive:**
<iframe width="100%" height="450" src="https://www.youtube.com/embed/r-GE-pD_xG4" title="FastAPI Request Body Deep Dive" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

**FastAPI Serialization & Responses:**
<iframe width="100%" height="450" src="https://www.youtube.com/embed/OkrDvk_qQ6M" title="FastAPI Serialization and Responses" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
""",
        "quiz_data": [
            {
                "id": 1,
                "question": "Which parameter helper is intended to add validation constraints to a query parameter?",
                "options": [
                    "`Query()`",
                    "`ForeignKey()`",
                    "`relationship()`",
                    "`Depends()` only",
                ],
                "correct_index": 0,
                "explanation": "`Query()` supplies metadata and constraints for query parameters, such as minimum or maximum values. `Path()` does the same for path values, while `Body()` describes request body input.",
            },
            {
                "id": 2,
                "question": "What response does FastAPI normally return when a request body fails Pydantic validation?",
                "options": [
                    "200 OK with invalid fields removed.",
                    "201 Created with an empty resource.",
                    "422 Unprocessable Entity with validation details.",
                    "500 Internal Server Error for every invalid client value.",
                ],
                "correct_index": 2,
                "explanation": "FastAPI validates the request body before the route handler runs and returns 422 with structured details when the payload does not satisfy its Pydantic schema.",
            },
            {
                "id": 3,
                "question": "Why should a create endpoint use a response model?",
                "options": [
                    "It filters and documents the public response shape so internal fields are not exposed accidentally.",
                    "It disables request validation.",
                    "It commits a database transaction automatically in every case.",
                    "It changes every response to status 200.",
                ],
                "correct_index": 0,
                "explanation": "A response model defines the output contract and filters data to its declared fields. It helps prevent internal-only values from leaking and keeps generated API documentation accurate.",
            },
        ],
    },
    {
        "ordering": 3,
        "title": "Dependency Injection and Middleware Architecture",
        "description": "Unlock FastAPI's powerful Dependency Injection system (Depends) and custom middleware architecture for authentication, logging, and security.",
        "video_url": "https://www.youtube.com/embed/1oWPUpMheGk",
        "content": """# Dependency Injection and Middleware Architecture

FastAPI dependencies provide reusable, composable logic for routes. Middleware wraps the application request/response cycle globally. Together they support clean database session management, authentication, request tracing, CORS, and security policies without duplicating infrastructure code in every handler.

## 1. The Power of `Depends`

`Depends()` declares that a route needs a value or capability supplied by another callable. FastAPI resolves the dependency, validates its inputs, and injects the result into the path operation. A dependency can provide a database session, the current authenticated user, a permission check, or parsed shared configuration.

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session

SessionDep = Annotated[Session, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_active_user)]

@router.get("/profile")
def read_profile(session: SessionDep, current_user: CurrentUserDep):
    ...
```

Dependencies make route requirements visible in the signature and can be overridden in tests. Authentication should identify the principal; authorization should enforce whether that principal may perform this operation on this resource. Never trust a client-supplied user ID as proof of identity.

## 2. Sub-dependencies & Yield

Dependencies can depend on other dependencies. A route may depend on an authenticated user, which in turn depends on a token parser and active-user lookup. FastAPI resolves this graph and can cache a dependency result during one request so shared dependencies are not needlessly repeated.

Use `yield` when a dependency owns a resource lifecycle. Code before `yield` acquires or configures the resource; code after `yield` runs during cleanup:

```python
def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

Keep transaction boundaries explicit. A request-scoped session should be closed after use, and failures should roll back pending changes. Do not share a synchronous SQLAlchemy session across concurrent tasks.

## 3. Middleware Architecture

Middleware wraps the entire ASGI application. An HTTP middleware can record a start time, call the next handler, then attach timing or correlation headers to the response. It is suitable for cross-cutting concerns that apply broadly, such as request IDs, security headers, compression, and CORS.

Middleware order matters: request handling passes through the stack in one order, and the response returns through it in reverse. Keep middleware small and avoid placing endpoint-specific business rules there. Authentication and resource authorization are usually clearer as dependencies close to the route that requires them.

```python
@app.middleware("http")
async def add_process_time(request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(time.perf_counter() - started)
    return response
```

Configure CORS with explicit trusted origins in production. Add security headers deliberately, avoid logging credentials or sensitive payloads, and test middleware behavior on success and error responses.

## 4. Choosing Between Dependencies and Middleware

Use a dependency when a particular route needs a value, resource, or authorization policy. Use middleware for behavior that should wrap most or all HTTP requests. This separation keeps shared infrastructure reusable while making each endpoint's requirements easy to inspect and test.

---
### Additional Video Resources

**Advanced FastAPI Middleware & Dependency Injection:**
<iframe width="100%" height="450" src="https://www.youtube.com/embed/nn0XzpYduA0" title="Advanced FastAPI Middleware and Dependency Injection" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
""",
        "quiz_data": [
            {
                "id": 1,
                "question": "What does FastAPI's `Depends()` primarily do?",
                "options": [
                    "Injects reusable values or capabilities such as a session or authenticated user into a route.",
                    "Creates a database table from every function parameter.",
                    "Replaces HTTP middleware and all application startup hooks.",
                    "Automatically grants admin privileges to the caller.",
                ],
                "correct_index": 0,
                "explanation": "Dependencies provide reusable, composable request-time values and behavior. They are commonly used for sessions, authentication, authorization, and shared parsing logic.",
            },
            {
                "id": 2,
                "question": "Why can a database dependency use `yield`?",
                "options": [
                    "To suspend SQL statements indefinitely.",
                    "To provide a resource to the route and run cleanup, such as closing the session, afterward.",
                    "To skip transaction rollback when an exception occurs.",
                    "To share one session globally across all requests.",
                ],
                "correct_index": 1,
                "explanation": "A yield dependency can acquire a resource before yielding it and perform teardown after the request finishes. This pattern is useful for reliably closing request-scoped database sessions.",
            },
            {
                "id": 3,
                "question": "Which responsibility is generally a better fit for middleware than a route-specific dependency?",
                "options": [
                    "Checking whether one user owns one particular course record.",
                    "Applying a request ID or timing header across most HTTP requests.",
                    "Validating one endpoint's nested request body.",
                    "Deciding whether a specific student may update a lesson.",
                ],
                "correct_index": 1,
                "explanation": "Middleware wraps the application-wide request/response cycle, making it suitable for cross-cutting behavior such as correlation IDs and timing. Resource-specific authorization and validation are clearer in dependencies or route logic.",
            },
        ],
    },
)


def validate_quiz(quiz_data: list[dict]) -> None:
    if len(quiz_data) != 3:
        raise ValueError("Each Module 2 lesson must have exactly three quiz questions.")
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
            raise ValueError("Each quiz item must have four options, a valid answer, and an explanation.")


def seed_module_2() -> None:
    for spec in LESSON_SPECS:
        validate_quiz(spec["quiz_data"])

    with SessionLocal() as session:
        with session.begin():
            track = session.scalar(select(Track).where(Track.slug == TRACK_SLUG))
            if track is None:
                raise LookupError(f"Track '{TRACK_SLUG}' was not found.")

            module = session.scalar(
                select(TrackModule).where(
                    TrackModule.track_id == track.id,
                    TrackModule.title == MODULE_TITLE,
                )
            )
            if module is None:
                raise LookupError(f"Module '{MODULE_TITLE}' was not found.")

            lessons = list(
                session.scalars(
                    select(Lesson)
                    .where(Lesson.module_id == module.id)
                    .order_by(Lesson.ordering, Lesson.id)
                )
            )
            lesson_by_order = {lesson.ordering: lesson for lesson in lessons}
            missing_orders = [
                spec["ordering"]
                for spec in LESSON_SPECS
                if spec["ordering"] not in lesson_by_order
            ]
            if missing_orders:
                raise LookupError(
                    f"Module 2 is missing lesson ordering(s): {missing_orders}."
                )

            for spec in LESSON_SPECS:
                lesson = lesson_by_order[spec["ordering"]]
                lesson.title = spec["title"]
                lesson.description = spec["description"]
                lesson.video_url = spec["video_url"]
                lesson.content = spec["content"]
                lesson.quiz_data = spec["quiz_data"]

            session.flush()
            for spec in LESSON_SPECS:
                lesson = lesson_by_order[spec["ordering"]]
                if (
                    lesson.title != spec["title"]
                    or lesson.description != spec["description"]
                    or lesson.video_url != spec["video_url"]
                    or lesson.content != spec["content"]
                    or lesson.quiz_data != spec["quiz_data"]
                ):
                    raise RuntimeError(
                        f"Lesson ordering {spec['ordering']} failed verification."
                    )

        for spec in LESSON_SPECS:
            print(
                f"Seeded Module 2 lesson {spec['ordering']}: {spec['title']} "
                f"({len(spec['quiz_data'])} quiz questions)."
            )


if __name__ == "__main__":
    seed_module_2()