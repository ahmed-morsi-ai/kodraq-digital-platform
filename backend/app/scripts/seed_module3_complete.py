from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.session import SessionLocal
from app.models.track import Lesson, Track, TrackModule

TRACK_SLUG = "backend-ai-engineering"
MODULE_TITLE = "Module 3: PostgreSQL, SQLAlchemy, and Alembic"

LESSON_SPECS = (
    {
        "ordering": 1,
        "title": "Relational Database Design & SQL Fundamentals",
        "description": (
            "Master relational database schema design, normalization, foreign keys, constraints, "
            "and raw SQL querying principles for production backends."
        ),
        "video_url": "https://www.youtube.com/embed/26ls5lNiijk",
        "content": """# Relational Database Design & SQL Fundamentals

A relational database stores facts in related tables and uses keys and constraints to preserve their meaning. Good schema design starts with the domain and expected access patterns, then makes important invariants explicit so they remain true even when multiple requests write concurrently.

## 1. Relational Schema Design & Normalization

Begin by identifying entities, their attributes, and the relationships between them. In a learning platform, `students`, `courses`, and `enrollments` are distinct entities. Each table should represent one kind of fact, and each row should have a stable primary key. A foreign key records a relationship, such as `enrollments.student_id` referring to `students.id`.

Relationship cardinality describes how records connect:

| Relationship | Example | Relational representation |
| --- | --- | --- |
| One-to-one | A user and one optional profile | A foreign key with a uniqueness constraint |
| One-to-many | One instructor owns multiple courses | A foreign key on the many-side table |
| Many-to-many | Students enroll in many courses | A junction table such as `enrollments` |

Normalization reduces duplication and update anomalies. First Normal Form (1NF) requires values to be atomic and repeating groups to be represented as rows. Second Normal Form (2NF) requires non-key attributes to depend on the whole key, especially when a composite key is used. Third Normal Form (3NF) removes transitive dependencies so non-key attributes describe the key, the whole key, and nothing but the key.

For example, avoid storing comma-separated course IDs in a student row. An `enrollments` table can represent each student-course association and hold relationship-specific facts such as enrollment date or status. Normalize first for correctness; denormalize only when measured query needs justify the extra consistency work.

## 2. Constraints & Data Integrity

Constraints make invalid states harder to store, regardless of which application path performs a write:

* `NOT NULL` requires a value for a column.
* `UNIQUE` prevents duplicate values, such as duplicate email addresses or duplicate student-course enrollment pairs.
* `CHECK` enforces a predicate, such as a non-negative price or a status from an allowed set.
* `PRIMARY KEY` uniquely identifies each row and is both unique and non-null.
* `FOREIGN KEY` ensures a referenced row exists and can define what happens when it is deleted.

Use `ON DELETE CASCADE` only when child rows have no independent meaning without their parent. For audit records or financial data, restriction or a deliberate soft-delete policy may be more appropriate. Application validation improves error messages, but database constraints remain essential protection against race conditions and alternate writers.

## 3. SQL Querying & Indexes

Use SQL to express the data you need, and inspect the query plan when performance matters:

```sql
SELECT c.id, c.title, COUNT(e.student_id) AS enrollment_count
FROM courses AS c
LEFT JOIN enrollments AS e ON e.course_id = c.id
WHERE c.is_published = TRUE
GROUP BY c.id, c.title
ORDER BY enrollment_count DESC;
```

`JOIN` combines related rows, `GROUP BY` calculates aggregates, and `WHERE` filters rows before grouping. Select only needed columns, use bound parameters for user input, and apply deterministic ordering when paginating.

A B-tree index is suitable for many equality, range, and ordered lookups. Index columns used frequently in filters, joins, and sorting, but avoid indexing every column: indexes consume storage and add work to inserts, updates, and deletes. Use `EXPLAIN` or `EXPLAIN ANALYZE` with representative data to confirm whether an index improves the query rather than assuming it does.

## 4. Production Design Checklist

Identify each entity and its ownership, choose keys deliberately, model many-to-many relations with junction tables, and enforce invariants in the database. Review common queries before adding indexes, and test constraints and transaction behavior under concurrent writes. A schema is a durable contract: changes should be reviewed and migrated safely rather than applied by hand in production.
""",
        "quiz_data": [
            {
                "id": 1,
                "question": "What is the main purpose of normalization in a relational schema?",
                "options": [
                    "To eliminate every foreign key from the database.",
                    "To reduce duplicated facts and avoid insert, update, and delete anomalies.",
                    "To store all entities in one wide table for easier querying.",
                    "To guarantee every query uses an index.",
                ],
                "correct_index": 1,
                "explanation": "Normalization separates independent facts into well-related tables, reducing duplication and anomalies. It does not remove relationships or guarantee a query plan; indexes and access patterns are considered separately.",
            },
            {
                "id": 2,
                "question": "How should a many-to-many relationship between students and courses usually be represented?",
                "options": [
                    "Store a comma-separated list of course IDs in each student row.",
                    "Add one nullable course_id column to the students table.",
                    "Create a junction table, such as enrollments, with foreign keys to both entities.",
                    "Duplicate the full student row once for every course.",
                ],
                "correct_index": 2,
                "explanation": "A junction table represents each association as a row with foreign keys to both related tables. It can also hold relationship attributes such as enrollment date and status.",
            },
            {
                "id": 3,
                "question": "Which statement about a B-tree index is accurate?",
                "options": [
                    "It improves every query and has no write or storage cost.",
                    "It can help equality, range, and ordered lookups, but adds storage and write overhead.",
                    "It replaces foreign-key constraints and transaction isolation.",
                    "It is only useful for columns containing JSON documents.",
                ],
                "correct_index": 1,
                "explanation": "B-tree indexes support many common lookup and ordering patterns, but each index consumes space and must be maintained during writes. Query plans and workload measurements should guide index choices.",
            },
        ],
    },
    {
        "ordering": 2,
        "title": "SQLAlchemy ORM Models and Session Management",
        "description": (
            "Bridge object-oriented Python code and relational databases using SQLAlchemy ORM, "
            "declarative models, relationships, and Unit of Work sessions."
        ),
        "video_url": "https://www.youtube.com/embed/529LYDgRTgQ",
        "content": """# SQLAlchemy ORM Models and Session Management

SQLAlchemy maps Python objects to relational tables while still allowing explicit SQL expressions and control over transactions. The ORM is most effective when developers understand both the object model and the SQL it emits.

## 1. SQLAlchemy Declarative Base & Models

Declarative models describe tables with Python classes. In SQLAlchemy 2.x, typed mappings use `Mapped` and `mapped_column` so Python annotations, column types, nullability, and defaults are visible together.

```python
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
```

Choose explicit nullability, uniqueness, constraints, and indexes based on domain rules and access patterns. Keep persistence models focused on database representation; use separate Pydantic schemas for API input and output when their contracts differ.

## 2. Relationships & Loading Strategies

ORM relationships connect mapped entities. `back_populates` makes the two directions explicit and keeps in-memory relationship state coherent:

```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Enrollment(Base):
    __tablename__ = "enrollments"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    course: Mapped[Course] = relationship(back_populates="enrollments")

Course.enrollments = relationship(back_populates="course")
```

Lazy loading can issue a query when a relationship is accessed. In a loop, this can create the N+1 problem: one query for the parent collection plus one query per parent. `selectinload` fetches related rows in a separate batched query; `joinedload` uses a SQL join and can be useful for suitable one-to-one or many-to-one paths. Choose based on cardinality and generated SQL, not habit.

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

statement = select(Course).options(selectinload(Course.enrollments))
courses = session.scalars(statement).all()
```

Inspect query counts and SQL in tests or development to catch accidental lazy loads. Avoid returning ORM graphs whose relationships trigger unpredictable database access during serialization.

## 3. Session Lifecycle & Unit of Work

A SQLAlchemy `Session` is a unit of work: it tracks objects, coordinates database operations, and manages a transaction. It is not itself the database, and a session should have a clear, bounded lifetime. In a web application, a common pattern is one session per request, created and closed through a dependency or context manager.

```python
with SessionLocal() as session:
    with session.begin():
        session.add(new_course)
```

The transaction context commits when the block succeeds and rolls back if an exception escapes. When managing transactions manually, call `commit()` only after all intended writes succeed, call `rollback()` on failure, and always close the session. Do not share one session concurrently between async tasks or unrelated requests.

Use `select()` and `session.scalars()` for SQLAlchemy 2.x queries. Keep transaction boundaries around a business operation so related writes succeed or fail together. Handle integrity errors at the application boundary and return safe domain-level errors rather than leaking raw database messages.

## 4. Practical ORM Workflow

Define mappings and constraints, create or evolve schema through migrations, write queries that match actual access paths, and inspect the emitted SQL. Test both object behavior and database behavior, including relationship loading, rollback, uniqueness violations, and concurrent updates. The ORM makes database work ergonomic; it does not remove the need to understand SQL or transaction semantics.
""",
        "quiz_data": [
            {
                "id": 1,
                "question": "What do `Mapped` and `mapped_column` provide in SQLAlchemy 2.x declarative models?",
                "options": [
                    "Typed declarations that map Python attributes to database columns.",
                    "Automatic API authentication for every model.",
                    "A command to generate Alembic revisions without metadata.",
                    "A guarantee that all database queries are asynchronous.",
                ],
                "correct_index": 0,
                "explanation": "`Mapped` and `mapped_column` express typed ORM attributes and their database-column configuration. They do not provide authentication, create migrations by themselves, or make synchronous queries asynchronous.",
            },
            {
                "id": 2,
                "question": "How can `selectinload` help address an N+1 relationship-loading problem?",
                "options": [
                    "It disables all relationship queries permanently.",
                    "It loads related rows in a batched follow-up query instead of issuing one query per parent.",
                    "It converts every relationship into a database foreign key.",
                    "It commits pending changes before each SELECT.",
                ],
                "correct_index": 1,
                "explanation": "`selectinload` fetches related records for a collection of parent rows using a batched query, avoiding one lazy-load query per parent. The best loading strategy depends on relationship shape and the generated SQL.",
            },
            {
                "id": 3,
                "question": "What is the role of a SQLAlchemy Session in the Unit of Work pattern?",
                "options": [
                    "It is a permanent replacement for PostgreSQL storage.",
                    "It tracks ORM changes and coordinates database operations within a bounded transaction lifecycle.",
                    "It guarantees the application has no database errors.",
                    "It should be shared globally across all concurrent requests.",
                ],
                "correct_index": 1,
                "explanation": "A Session tracks changes and coordinates persistence within a transaction. It should have a bounded lifetime, be committed or rolled back intentionally, and be closed rather than shared globally across concurrent requests.",
            },
        ],
    },
    {
        "ordering": 3,
        "title": "Database Migrations with Alembic",
        "description": (
            "Evolve your PostgreSQL database schemas safely and predictably over time using Alembic "
            "version-controlled migration scripts."
        ),
        "video_url": "https://www.youtube.com/embed/e8NnDz8uT7o",
        "content": """# Database Migrations with Alembic

Applications evolve, and their database schemas must evolve with them. Alembic records schema changes as ordered, reviewable Python revisions so development, staging, and production can move through the same version history without manually editing each database.

## 1. Why Database Migrations?

A migration describes a schema transition, such as adding a nullable column, creating an index, or introducing a new table. Without versioned migrations, environments drift: one developer may have a local column that production lacks, or a deployment may depend on a schema change that was never applied elsewhere.

Treat migrations as deployment code. Review generated SQL, consider existing data, and plan compatibility between old and new application versions. For a required column, a safe rollout may add it as nullable, backfill existing rows, deploy code that writes it, and only then add a `NOT NULL` constraint. Destructive changes often require a staged deprecation rather than one release.

## 2. Setting Up Alembic with SQLAlchemy

Initialize Alembic in the project and configure `env.py` with the application's SQLAlchemy metadata. With a declarative base, `target_metadata` should point to `Base.metadata`, and all model modules must be imported so their tables are registered before autogeneration runs.

```python
from app.models.base import Base
from app.models import course, enrollment  # Import models to register metadata

target_metadata = Base.metadata
```

Keep database credentials in environment-based settings or a secret manager, not committed migration files. Alembic's configuration should obtain the connection URL from the same trusted configuration source as the application, with credentials redacted from logs. Use a dedicated migration role with only the permissions needed to alter the schema.

## 3. Generating & Executing Migrations

Autogeneration compares model metadata with the current schema and produces a candidate revision:

```console
alembic revision --autogenerate -m "add course visibility"
```

Review every generated `upgrade()` and `downgrade()` operation. Autogenerate cannot infer every data migration or business intent; renames may appear as drop-and-add operations, and backfills often need hand-written SQL or Python. A downgrade should reverse the schema change where that is safe, but dropping newly written data may make rollback destructive.

```console
alembic upgrade head
alembic downgrade -1
alembic current
alembic history
```

`upgrade head` applies revisions up to the latest head. A downgrade moves the schema to an earlier revision and should be tested against realistic data. Test migrations from both an empty database and a representative prior schema, and include failure/recovery steps in deployment plans.

## 4. Safe Production Migration Workflow

Back up important data, test migration duration and locking behavior, and prefer additive, backward-compatible changes during rolling deployments. Large table rewrites may need batching or online techniques. Coordinate application and migration order so no running code reads a column before it exists or writes a representation that older code cannot handle.

Track the applied revision in Alembic's version table, run migrations as an explicit deployment step, and monitor database health afterward. A successful command is not enough: verify constraints, indexes, row counts, and application behavior before considering a migration complete.
""",
        "quiz_data": [
            {
                "id": 1,
                "question": "Why should database schema changes be managed with versioned migrations?",
                "options": [
                    "To ensure each environment can apply the same reviewed schema transitions in order.",
                    "To avoid testing schema changes against existing data.",
                    "To let every developer make unrelated manual production edits.",
                    "To guarantee that application code never needs deployment coordination.",
                ],
                "correct_index": 0,
                "explanation": "Versioned migrations make schema evolution reproducible across environments and reviewable as code. They do not remove the need to test against real data or coordinate compatible application deployments.",
            },
            {
                "id": 2,
                "question": "What should a developer do after Alembic generates an autogeneration revision?",
                "options": [
                    "Apply it immediately without opening the file.",
                    "Review and test the upgrade and downgrade operations, including data and compatibility effects.",
                    "Delete the downgrade function because Alembic always reconstructs lost data.",
                    "Commit database credentials into the revision for repeatability.",
                ],
                "correct_index": 1,
                "explanation": "Autogeneration creates a candidate based on metadata differences, but it cannot infer every rename, backfill, or deployment concern. Review and test both directions and keep secrets out of migration files.",
            },
            {
                "id": 3,
                "question": "Which rollout is safer when adding a required column to a populated production table?",
                "options": [
                    "Drop the table and recreate it with the new column.",
                    "Add it as nullable, backfill existing rows, deploy compatible writes, then enforce NOT NULL.",
                    "Add it as NOT NULL with no default and assume existing rows are filled automatically.",
                    "Change production manually and skip migration history.",
                ],
                "correct_index": 1,
                "explanation": "A staged additive rollout lets old and new application versions coexist while existing data is backfilled. After all rows and writers satisfy the rule, a later migration can safely enforce NOT NULL.",
            },
        ],
    },
)


def validate_quiz(quiz_data: list[dict]) -> None:
    if len(quiz_data) != 3:
        raise ValueError("Each Module 3 lesson must have exactly three quiz questions.")
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
            raise ValueError(
                "Each quiz question must have four options, a valid answer, and an explanation."
            )


def seed_module_3() -> None:
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
                    f"Module 3 is missing lesson ordering(s): {missing_orders}."
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
                f"Seeded Module 3 lesson {spec['ordering']}: {spec['title']} "
                f"({len(spec['quiz_data'])} quiz questions)."
            )


if __name__ == "__main__":
    seed_module_3()