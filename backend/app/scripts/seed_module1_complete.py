from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.session import SessionLocal
from app.models.track import Lesson, Track, TrackModule

TRACK_SLUG = "backend-ai-engineering"
MODULE_TITLE = "Module 1: Advanced Python & Engineering Practices"

LESSON_SPECS = (
    {
        "ordering": 1,
        "title": "Python Type Hints, Pydantic, and Data Validation",
        "description": "Master robust Python development using static typing, type hints, and strict runtime data validation with Pydantic.",
        "video_url": "https://www.youtube.com/embed/RwH2UzC2rIo",
        "content": """# Python Type Hints, Pydantic, and Data Validation

Transitioning from a dynamic scripting mindset to robust software engineering requires mastering Python's type system and runtime validation.

### 1. Static Typing in a Dynamic Language (Type Hints)

Python is dynamically typed, meaning variables can refer to values of different types at runtime. This flexibility is useful, but in a large codebase it can make incorrect assumptions hard to detect. Type hints (introduced in PEP 484) document intended inputs and outputs and allow tools such as mypy, Pyright, and IDE analyzers to find many mistakes before execution. Unless a runtime library enforces them, annotations do not prevent a call with the wrong value.

```python
def process_user(user_id: int) -> dict[str, object]:
    return {"id": user_id, "active": True}
```

Use `list[str]` for a collection of strings, `int | None` for an optional integer, and `dict[str, object]` when mapping keys to values of varying types. Prefer precise domain types over `Any`; `Any` opts out of many static checks. Type annotations should clarify a boundary, not merely decorate every line.

### 2. Runtime Enforcement with Pydantic

Type hints alone do not validate runtime input. Data arriving from HTTP clients, environment variables, files, or message queues is untrusted until parsed. Pydantic models define a runtime schema, validate values, and provide structured errors suitable for an API response.

```python
from pydantic import BaseModel, Field

class EnrollmentCreate(BaseModel):
    course_id: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=500)
```

For example, a request containing `{"course_id": "42"}` may be parsed into an integer under Pydantic's configured coercion rules. A value such as `"many"` cannot be parsed and produces a validation error identifying the field. FastAPI uses request schemas to validate payloads and document the contract in OpenAPI.

### 3. Advanced Data Validation

Field constraints can express basic rules such as positive IDs, bounded strings, and valid list sizes. For domain-specific rules, Pydantic validators can check relationships between values or normalize input. In Pydantic v2, use `@field_validator` for a field and `@model_validator` when validation depends on multiple fields.

Keep validation responsibilities clear: Pydantic checks shape and local invariants; application services enforce rules that depend on current database state, such as whether a course still has capacity. Return safe, actionable validation messages without exposing secrets or internal traces.

### 4. A Reliable Data Boundary

Treat parsing as an explicit boundary between external representations and internal values. Test valid values, malformed types, missing fields, boundary values, and normalization behavior. Keep schemas focused on input or output contracts so changes to persistence models do not accidentally change the public API.

---
### Advanced Resources: Pydantic & Data Validation

**Pydantic Deep Dive:**
<iframe width="100%" height="450" src="https://www.youtube.com/embed/M81pfi64eeM" title="Pydantic Deep Dive" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

**Data Validation Strategies:**
<iframe width="100%" height="450" src="https://www.youtube.com/embed/M81pfi64eeM" title="Data Validation Strategies" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
""",
        "quiz_data": [
            {
                "id": 1,
                "question": "Does Python's built-in type hinting prevent execution at runtime when a value has the wrong type?",
                "options": [
                    "Yes, Python always raises TypeError before entering the function.",
                    "No. By default, hints support documentation and static analysis but are not enforced by the runtime.",
                    "Yes, but only for functions defined in Python 3.10 or later.",
                    "No. Hints silently convert every value to the annotated type.",
                ],
                "correct_index": 1,
                "explanation": "Python does not enforce ordinary annotations at runtime. Static analyzers and IDEs can use them to detect likely mistakes; a runtime validation library such as Pydantic is needed to validate incoming data.",
            },
            {
                "id": 2,
                "question": "What happens when Pydantic cannot parse input into a declared field type?",
                "options": [
                    "It always substitutes None for the invalid value.",
                    "It exits the whole Python process with SystemExit.",
                    "It raises a ValidationError containing details about the invalid field.",
                    "It silently ignores the field and reports success.",
                ],
                "correct_index": 2,
                "explanation": "Pydantic reports structured validation details, including the field and reason for failure. API frameworks such as FastAPI can turn request validation failures into client error responses without exposing server internals.",
            },
            {
                "id": 3,
                "question": "Which Pydantic v2 decorator is intended for custom validation of one field?",
                "options": [
                    "`@field_validator`",
                    "`@dataclass`",
                    "`@classmethodproperty`",
                    "Pydantic does not support custom validation.",
                ],
                "correct_index": 0,
                "explanation": "Pydantic v2's `@field_validator` attaches custom validation or normalization to a field. Use `@model_validator` when the rule depends on multiple fields.",
            },
        ],
    },
    {
        "ordering": 2,
        "title": "Advanced OOP, Dataclasses, and Protocols",
        "description": "Elevate your object-oriented design using Python Dataclasses, structural subtyping (Protocols), and advanced OOP patterns.",
        "video_url": "https://www.youtube.com/embed/Ej_02ICOIgs",
        "content": """# Advanced OOP, Dataclasses, and Protocols

To build scalable backend architecture, you must understand how Python models data and behavior, defines object contracts, and composes reusable components. The aim is not to make every concept a class; it is to choose boundaries that make behavior explicit and changes testable.

### 1. Advanced Object-Oriented Design

Classes combine state and behavior. Encapsulation keeps implementation details behind a small public interface. Inheritance can reuse or specialize behavior, but deep inheritance chains make dependencies difficult to see. Prefer composition when an object can delegate work to focused collaborators.

Mixins can add a narrow, reusable behavior to unrelated classes, but should remain small and avoid surprising initialization order. Python's special methods such as `__repr__`, `__eq__`, `__iter__`, and `__call__` let objects participate in standard language operations. Implement only the behavior that makes the object's contract more predictable.

```python
class RetryPolicy:
    def __init__(self, attempts: int) -> None:
        self.attempts = attempts

    def allows_retry(self, attempt: int) -> bool:
        return attempt < self.attempts
```

### 2. Dataclasses for Domain Values

The `@dataclass` decorator generates common methods such as `__init__` and `__repr__` from annotated fields. Dataclasses are useful for small domain values and internal records where a full validation framework would be unnecessary.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Money:
    amount_cents: int
    currency: str
```

`frozen=True` prevents reassignment of fields after construction, which helps make value objects predictable; it does not recursively freeze mutable objects held by a field. Use `default_factory` for mutable defaults such as lists. `__post_init__` can check invariants after the generated initializer runs, though validation that parses untrusted external data is often better handled by a boundary schema.

### 3. Protocols and Structural Subtyping

Python's duck typing allows code to use an object based on the behavior it provides. `typing.Protocol` makes this style visible to static type checkers without requiring an implementation to inherit from the protocol. This is called structural subtyping.

```python
from typing import Protocol

class UserRepository(Protocol):
    def get_by_id(self, user_id: int) -> "User | None": ...

def load_profile(repository: UserRepository, user_id: int) -> "User | None":
    return repository.get_by_id(user_id)
```

An in-memory fake and a PostgreSQL-backed repository can both satisfy the protocol if they provide the required method with a compatible signature. This makes application services easier to test and reduces coupling to a particular persistence implementation. Use an abstract base class when explicit shared implementation or runtime identity checks are important; use a protocol when the contract matters more than the inheritance relationship.

### 4. Choosing the Right Abstraction

Use a plain function for a simple stateless operation, a dataclass for a compact value record, a class when state and behavior form a cohesive object, and a protocol when callers need a substitutable interface. Favor readable composition over abstraction for its own sake, and test observable behavior rather than private method calls.

---
### Additional Video Resources

**Advanced OOP Patterns (Part 2):**
<iframe width="100%" height="450" src="https://www.youtube.com/embed/IbMDCwVm63M" title="Advanced OOP Patterns Part 2" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

**Mastering Python Dataclasses:**
<iframe width="100%" height="450" src="https://www.youtube.com/embed/aH5sgOxuCnk" title="Mastering Python Dataclasses" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

**Understanding Protocols in Python:**
<iframe width="100%" height="450" src="https://www.youtube.com/embed/Lddegb2ToNY" title="Understanding Protocols in Python" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
""",
        "quiz_data": [
            {
                "id": 1,
                "question": "What is the primary benefit of the `@dataclass` decorator?",
                "options": [
                    "It automatically makes every method execute faster.",
                    "It generates common boilerplate methods such as `__init__` and `__repr__` from annotated fields.",
                    "It turns the class into a PostgreSQL table automatically.",
                    "It prevents the class from being composed with other objects.",
                ],
                "correct_index": 1,
                "explanation": "Dataclasses generate common methods from the declared fields, reducing repetitive code. They do not automatically create database tables or guarantee faster execution.",
            },
            {
                "id": 2,
                "question": "How can you prevent reassignment of dataclass fields after initialization?",
                "options": [
                    "Inherit from a built-in `ImmutableClass`.",
                    "Prefix every field name with two underscores.",
                    "Use `@dataclass(frozen=True)`, while remembering nested mutable values are not recursively frozen.",
                    "Declare the fields with the `const` keyword.",
                ],
                "correct_index": 2,
                "explanation": "The `frozen=True` option blocks normal field reassignment after initialization. It does not make mutable objects stored inside fields deeply immutable.",
            },
            {
                "id": 3,
                "question": "What is the key distinction between an abstract base class and a Protocol?",
                "options": [
                    "Protocols always require explicit inheritance, while abstract base classes never do.",
                    "Abstract base classes use structural typing and Protocols require nominal inheritance.",
                    "An ABC typically establishes an explicit inheritance relationship, while a Protocol can be satisfied structurally by matching its members.",
                    "Protocols cannot declare methods.",
                ],
                "correct_index": 2,
                "explanation": "Protocols describe a structural contract: a class can be compatible by implementing the required members without inheriting from the protocol. Abstract base classes commonly use nominal inheritance and can share implementation.",
            },
        ],
    },
    {
        "ordering": 3,
        "title": "Async/Await and Concurrency in Python",
        "description": "Unlock high-performance Python by mastering asynchronous programming, event loops, and I/O-bound concurrency.",
        "video_url": "https://www.youtube.com/embed/t5Bo1Je9EmE",
        "content": """# Async/Await and Concurrency in Python

Synchronous code generally waits for one operation to finish before moving to the next. When a backend spends time waiting for a database, network service, or file operation, asynchronous I/O can let the process make progress on other work during that wait. Async is a coordination model, not a way to make CPU-heavy code automatically faster.

### 1. Concurrency vs. Parallelism

* **Concurrency:** Multiple tasks make progress over overlapping periods. A single event-loop thread can switch to another task while the current task waits for I/O.
* **Parallelism:** Multiple operations execute at the same instant, typically using multiple CPU cores or processes.

Concurrency can improve throughput for I/O-bound workloads. Parallel execution is usually needed to use multiple cores for CPU-bound computation; Python's `asyncio` alone does not provide that parallelism.

### 2. The Event Loop and Coroutines

An `async def` function creates a coroutine function. Calling it returns a coroutine object; it does not run the body immediately. The event loop schedules coroutines as tasks and resumes them when awaited operations become ready.

```python
import asyncio

async def fetch_profile(client, user_id: int):
    response = await client.get(f"/users/{user_id}")
    return response.json()

async def main():
    profiles = await asyncio.gather(
        fetch_profile(client, 10),
        fetch_profile(client, 11),
    )
    return profiles
```

`await` suspends the current coroutine at an awaitable operation and yields control to the event loop. Use `asyncio.gather` or task groups when operations are independent and can safely run concurrently. Set timeouts, propagate cancellation, and handle partial failures deliberately.

### 3. I/O-Bound vs. CPU-Bound Work

Asyncio is well suited to I/O-bound tasks such as HTTP requests and asynchronous database queries, provided the libraries themselves are non-blocking. Calling a synchronous blocking function inside an async route can stall the event loop and delay unrelated requests.

Heavy CPU work such as image encoding or large numerical calculations can also block the loop. Move that work to a process pool, worker queue, or separate service when appropriate. Threads can help with some blocking I/O integrations, while processes are a common option for CPU-bound work.

### 4. Safe Production Concurrency

Bound concurrency so a burst of requests does not overwhelm a provider or database connection pool. Give external operations timeouts, close clients and sessions with context managers, and ensure cancellation does not leave partially committed state. Do not share a non-concurrency-safe database session across simultaneous tasks.

Measure latency and throughput under representative load before choosing sync or async interfaces. Use async when the full dependency path can benefit from cooperative I/O; do not convert code merely because `async` looks modern.

---
### Additional Video Resources

**Asyncio Deeply Explained:**
<iframe width="100%" height="450" src="https://www.youtube.com/embed/oAkLSJNr5zY" title="Asyncio Deeply Explained" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

**Concurrency, Threading, and Multiprocessing:**
<iframe width="100%" height="450" src="https://www.youtube.com/embed/S05-MZAJqNM" title="Concurrency, Threading, and Multiprocessing" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
""",
        "quiz_data": [
            {
                "id": 1,
                "question": "What does `await` do when a coroutine is waiting for an asynchronous operation?",
                "options": [
                    "It permanently pauses the CPU until the operation finishes.",
                    "It suspends the current coroutine and yields control so the event loop can run other tasks.",
                    "It always creates a new operating-system thread.",
                    "It converts any synchronous function into a non-blocking function.",
                ],
                "correct_index": 1,
                "explanation": "Awaiting an asynchronous operation lets the current coroutine pause while the event loop schedules other ready work. It does not create a thread or make a blocking synchronous function non-blocking.",
            },
            {
                "id": 2,
                "question": "Which workload is generally a strong fit for asyncio?",
                "options": [
                    "A CPU-heavy matrix multiplication that occupies the processor continuously.",
                    "Video encoding that saturates every CPU core.",
                    "Many concurrent HTTP requests that spend time waiting on network responses.",
                    "Sorting a large in-memory array using a synchronous algorithm.",
                ],
                "correct_index": 2,
                "explanation": "Asyncio is most beneficial when tasks spend significant time waiting on non-blocking I/O. CPU-bound work can block the event loop and may need a process pool or worker service instead.",
            },
            {
                "id": 3,
                "question": "What happens when an `async def` function is called without `await` or task scheduling?",
                "options": [
                    "Its body executes synchronously before the call returns.",
                    "It returns a coroutine object, but its body does not run until the coroutine is awaited or scheduled.",
                    "Python automatically creates a background process for it.",
                    "It always raises `SystemExit`.",
                ],
                "correct_index": 1,
                "explanation": "Calling an async function constructs a coroutine object. The event loop must await or schedule that coroutine for its body to execute.",
            },
        ],
    },
)


def validate_quiz(quiz_data: list[dict]) -> None:
    if len(quiz_data) != 3:
        raise ValueError("Each Module 1 lesson must have exactly three quiz questions.")
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
            raise ValueError("Every quiz item must have four options, a valid answer, and an explanation.")


def seed_module_1() -> None:
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
                    .order_by(Lesson.ordering)
                )
            )
            lesson_by_order = {lesson.ordering: lesson for lesson in lessons}
            missing_orderings = [
                spec["ordering"]
                for spec in LESSON_SPECS
                if spec["ordering"] not in lesson_by_order
            ]
            if missing_orderings:
                raise LookupError(
                    f"Module 1 is missing lesson ordering(s): {missing_orderings}."
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
                f"Seeded Module 1 lesson {spec['ordering']}: {spec['title']} "
                f"({len(spec['quiz_data'])} quiz questions)."
            )


if __name__ == "__main__":
    seed_module_1()