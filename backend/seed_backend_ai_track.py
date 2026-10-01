from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.pricing import BACKEND_AI_TRACK_PRICE_EGP
from app.db.session import SessionLocal
from app.models.assignment import Assignment
from app.models.track import Lesson, Track, TrackModule

TRACK_NAME = "Backend & AI Engineering"
TRACK_SLUG = "backend-ai-engineering"
LESSON_1_TITLE = "Introduction to System Design & API Boundaries"
LESSON_1_DESCRIPTION = (
    "Learn how to turn product requirements into system components and clear API contracts. "
    "Understand functional vs non-functional requirements and layered architecture."
)
LESSON_1_VIDEO_URL = "https://www.youtube.com/embed/m8Icp_Cid5o"
MODULE_0_LESSONS = (
    {
        "title": LESSON_1_TITLE,
        "description": LESSON_1_DESCRIPTION,
        "content": LESSON_1_DESCRIPTION,
        "video_url": LESSON_1_VIDEO_URL,
    },
    {
        "title": "The Complete Request/Response Lifecycle",
        "description": (
            "Trace an HTTP request end-to-end: from client DNS and reverse proxy "
            "through ASGI server routing, Pydantic validation, auth guards, DB "
            "transactions, and serialized JSON responses."
        ),
        "content": "Trace the request from the client through the backend pipeline and back.",
        "video_url": "https://www.youtube.com/embed/tLzM-QQvvUo",
    },
    {
        "title": "Understanding Data Flow & Statelessness",
        "description": (
            "Master data movement through backend architectures: differentiate "
            "stateful vs. stateless services, durable persistence, request-scoped "
            "memory, and horizontal scaling strategies."
        ),
        "content": "Follow application data through requests, services, storage, and caches.",
        "video_url": "https://www.youtube.com/embed/z8N3dlsTvhE",
    },
)
TRACK_DESCRIPTION = (
    "A complete career-transformation path from programming foundations to "
    "production-ready backend and AI engineering. Progress through eight "
    "hands-on modules, build portfolio projects, and graduate with a deployed "
    "capstone. Top performers with high assessment results have a strong "
    "likelihood of job placement. Includes a 100% money-back guarantee."
)

CURRICULUM = (
    {
        "title": "Module 0: Backend Mindset & Architecture",
        "description": "Develop a systems view of backend work by defining API boundaries, tracing requests end to end, and reasoning about data flow and stateless services.",
        "lessons": MODULE_0_LESSONS,
        "assignment": {
            "title": "Design and Trace a Backend Request",
            "description": "Turn a course-enrollment requirement into a testable API contract and architecture sketch.",
            "instructions": "Document request/response schemas, authorization rules, state transitions, and expected error statuses. Implement a small endpoint skeleton, add tests for success and failure cases, and submit an architecture diagram plus a short decision record.",
            "difficulty": "beginner",
            "estimated_minutes": 150,
        },
    },
    {
        "title": "Module 1: Advanced Python & Engineering Practices",
        "description": "Build reliable Python services with runtime data validation, expressive object and interface models, and concurrency patterns suited to real workloads.",
        "lessons": (
            (
                "Python Type Hints, Pydantic, and Data Validation",
                "Use annotations to make function and data contracts explicit, then apply Pydantic models to parse and validate untrusted input. Practice field constraints, nested models, serialization, and useful validation errors while keeping static type checking distinct from runtime validation.",
            ),
            (
                "Advanced OOP, Dataclasses, and Protocols",
                "Model cohesive behavior with classes while favoring composition over deep inheritance. Use dataclasses for lightweight domain values, protocols for structural interfaces, and immutable or carefully controlled state to make components easier to substitute, test, and maintain.",
            ),
            (
                "Async/Await and Concurrency in Python",
                "Understand coroutines, the event loop, and when asynchronous I/O improves throughput. Coordinate concurrent tasks safely, set timeouts, handle cancellation and exceptions, and avoid blocking the event loop with CPU-bound work or synchronous calls.",
            ),
        ),
        "assignment": {
            "title": "Build a Tested Data Importer",
            "description": "Create a typed importer that validates records and reports row-level errors without sharing mutable state.",
            "instructions": "Implement parsing, validation, and aggregation as separate functions. Support UTF-8 and empty files, reject invalid values with line numbers, and test repeated runs, failure cleanup, and at least one large synthetic input. Include the test output and explain what is streamed versus held in memory.",
            "difficulty": "intermediate",
            "estimated_minutes": 210,
        },
    },
    {
        "title": "Module 2: FastAPI and Production API Design",
        "description": "Build maintainable production APIs with a deliberate FastAPI project structure, validated HTTP operations, dependency injection, and middleware boundaries.",
        "lessons": (
            (
                "Setting up FastAPI and Project Structure",
                "Create a FastAPI application with configuration, routers, schemas, services, and persistence organized by responsibility. Add OpenAPI metadata, environment-based settings, and a predictable application entry point that supports both local development and automated tests.",
            ),
            (
                "Request Validation, Query Params, and Path Operations",
                "Define path operations with typed path, query, header, and body parameters. Apply Pydantic constraints, defaults, response models, and appropriate HTTP methods and status codes; then inspect generated OpenAPI documentation and test both valid and invalid requests.",
            ),
            (
                "Dependency Injection and Middleware Architecture",
                "Use FastAPI dependencies to provide database sessions, authenticated principals, and reusable policy checks with clear lifetimes. Add middleware for cross-cutting concerns such as request IDs and timing, understand execution order, and keep business rules in application services rather than middleware.",
            ),
        ),
        "assignment": {
            "title": "Ship a Versioned Course API",
            "description": "Implement a documented API for tracks, modules, and lessons with validation and pagination.",
            "instructions": "Create list/detail endpoints and one state-changing endpoint. Add response schemas, pagination bounds, error handling, and OpenAPI tags. Write integration tests for valid input, missing records, malformed input, and unauthorized access; include a sample curl session.",
            "difficulty": "intermediate",
            "estimated_minutes": 240,
        },
    },
    {
        "title": "Module 3: PostgreSQL, SQLAlchemy, and Alembic",
        "description": "Design relational schemas, work confidently with SQL and SQLAlchemy sessions, and evolve PostgreSQL databases through controlled migrations.",
        "lessons": (
            (
                "Relational Database Design & SQL Fundamentals",
                "Translate domain requirements into normalized tables and relationships with primary keys, foreign keys, and explicit constraints. Practice SELECT, JOIN, filtering, grouping, and transactions, and use indexes and query plans to understand how PostgreSQL executes common access patterns.",
            ),
            (
                "SQLAlchemy ORM Models and Session Management",
                "Map database tables with SQLAlchemy models and relationships, query with the 2.x select API, and manage sessions and transactions at request boundaries. Choose relationship loading deliberately, detect N+1 queries, and avoid sharing a session across concurrent tasks.",
            ),
            (
                "Database Migrations with Alembic",
                "Configure Alembic against application metadata, generate and review migration revisions, and apply or revert schema changes safely. Plan data backfills and deployment compatibility so application releases do not lose data or break while old and new code overlap.",
            ),
        ),
        "assignment": {
            "title": "Model and Migrate a Learning Catalog",
            "description": "Create the relational schema for courses, modules, lessons, and enrollments with migration history.",
            "instructions": "Add foreign keys, uniqueness and check constraints, plus indexes justified by query patterns. Create an Alembic migration, seed representative records, test transaction rollback, and demonstrate that duplicate enrollment and invalid references are rejected.",
            "difficulty": "intermediate",
            "estimated_minutes": 240,
        },
    },
    {
        "title": "Module 4: Authentication, JWT, and API Security",
        "description": "Protect user credentials and API resources with secure password storage, token-based authentication, and server-enforced authorization policies.",
        "lessons": (
            (
                "Password Hashing with Passlib and Security Best Practices",
                "Hash passwords with Passlib using an appropriate adaptive algorithm and verify them without ever storing plaintext credentials. Apply safe secret handling, input limits, generic authentication errors, and least-privilege defaults while protecting sensitive data in logs and configuration.",
            ),
            (
                "Implementing JWT Tokens and OAuth2 Flows",
                "Implement an OAuth2 password-bearer flow that issues and validates signed JWT access tokens. Understand claims, signing keys, expiration, token verification, and how authentication dependencies establish the current user without confusing identity with permission.",
            ),
            (
                "Role-Based Access Control (RBAC) and Admin Guards",
                "Define roles and permissions as explicit authorization rules, then enforce them on protected operations using the authenticated principal. Guard administrative actions, verify resource ownership, prevent insecure direct-object references, and test forbidden, inactive-user, and cross-role access cases.",
            ),
        ),
        "assignment": {
            "title": "Secure a Student and Admin API",
            "description": "Add JWT authentication and role-aware access checks to a course management API.",
            "instructions": "Implement registration/login, password hashing, token verification, and per-resource ownership checks. Students may view their own enrollments; admins may manage all enrollments. Add tests proving cross-user reads/writes fail and ensure logs never contain credentials or tokens.",
            "difficulty": "advanced",
            "estimated_minutes": 270,
        },
    },
    {
        "title": "Module 5: Gemini, AI Integration, and RAG",
        "description": "Integrate Gemini behind reliable backend interfaces and build retrieval-augmented generation workflows that ground answers in authorized source material.",
        "lessons": (
            (
                "Integrating Google GenAI SDK in Backend Services",
                "Configure the official Google GenAI SDK with server-side credentials and application settings. Call generation APIs from a service layer, shape system instructions and model parameters, manage response and token metadata, and keep provider-specific details out of public API contracts.",
            ),
            (
                "Building AI Gateways and Error Handling",
                "Create an AI gateway that centralizes provider configuration, timeouts, retries, rate limits, and response normalization. Handle quota, network, safety, and malformed-response failures with bounded retry policies and useful application errors while protecting keys and avoiding sensitive prompt logging.",
            ),
            (
                "Grounded RAG Systems and Context Injection",
                "Prepare and chunk trusted documents, retrieve relevant passages, and inject bounded context into a prompt with clear source boundaries. Require answers to rely on supplied evidence, handle insufficient context transparently, enforce user or tenant access during retrieval, and evaluate relevance, citations, factuality, latency, and token cost.",
            ),
        ),
        "assignment": {
            "title": "Build a Grounded Course Tutor",
            "description": "Create a Gemini-backed RAG endpoint that answers from an authorized lesson corpus.",
            "instructions": "Implement ingestion, chunking, retrieval, prompt construction, and SDK generation. Keep the API key server-side, return a clear no-evidence response, and log token usage without logging secrets. Include tests for relevant retrieval, irrelevant queries, provider errors, and user/track isolation.",
            "difficulty": "advanced",
            "estimated_minutes": 300,
        },
    },
    {
        "title": "Module 6: Docker, DevOps, and Production Operations",
        "description": "Package and operate backend services with Docker, coordinate dependent services, and automate quality gates through reliable CI/CD workflows.",
        "lessons": (
            (
                "Containerizing FastAPI and PostgreSQL with Docker",
                "Write reproducible Docker images for a FastAPI application and PostgreSQL, configure ports, networks, persistent database storage, and health checks, and keep secrets out of image layers. Understand container processes, image builds, and the boundary between application and database containers.",
            ),
            (
                "Multi-Container Orchestration using Docker Compose",
                "Define API and database services in a Compose configuration with environment settings, named volumes, service discovery, startup dependencies, and readiness checks. Start, inspect, and troubleshoot the complete local stack, and distinguish process startup order from actual service readiness.",
            ),
            (
                "CI/CD Pipelines and Automated Testing",
                "Build a CI pipeline that installs dependencies, runs linting and unit or integration tests, and builds the production image before deployment. Use automated checks as release gates, manage deployment configuration securely, and make failures visible through actionable test output and health checks.",
            ),
        ),
        "assignment": {
            "title": "Deploy a Reproducible API Stack",
            "description": "Containerize the API and its data dependencies with a repeatable production-style workflow.",
            "instructions": "Build a Docker image and Compose stack, inject secrets through runtime configuration, add readiness checks, and document migration steps. Provide a CI workflow that runs focused tests and lint before image build; demonstrate recovery from a failed health check.",
            "difficulty": "advanced",
            "estimated_minutes": 270,
        },
    },
    {
        "title": "Module 7: Graduation Project and Career Readiness",
        "description": "Synthesize backend and AI engineering skills in a scoped capstone, then prepare clear portfolio evidence and practical job-search materials.",
        "lessons": (
            (
                "Capstone Project Architecture and Requirements",
                "Translate a real user problem into measurable requirements, acceptance criteria, and a bounded project scope. Produce an architecture diagram, API contract, relational data model, security considerations, delivery milestones, and a test strategy before implementation begins.",
            ),
            (
                "Preparing Your Portfolio and Technical CV",
                "Present the capstone as credible engineering evidence with a concise project summary, clear README, architecture decisions, API documentation, deployment instructions, and test results. Tailor a technical CV to demonstrate relevant skills and explain your individual contributions with specific outcomes.",
            ),
            (
                "Interview Preparation and Job Market Readiness",
                "Practice explaining system design choices, Python and database fundamentals, API security, debugging, and AI integration trade-offs. Prepare structured project walkthroughs, review common technical interview formats, and build a focused application and follow-up routine for backend engineering roles.",
            ),
        ),
        "assignment": {
            "title": "Graduate Capstone: Production-Ready AI Service",
            "description": "Deliver a complete, deployed backend product with secure accounts, PostgreSQL data, and a grounded AI feature.",
            "instructions": "Submit a live or reproducible deployment, source repository, API documentation, architecture diagram, migration history, security and failure-path tests, and a demo. Evaluation covers correctness, security, data integrity, retrieval grounding, observability, and clarity of technical decisions.",
            "difficulty": "advanced",
            "estimated_minutes": 600,
        },
    },
)


def seed_backend_ai_track(session: Session) -> tuple[Track, int, int, int]:
    track = session.scalar(select(Track).where(Track.slug == TRACK_SLUG))
    if track is None:
        track = Track(slug=TRACK_SLUG, name=TRACK_NAME)
        session.add(track)

    track.name = TRACK_NAME
    track.description = TRACK_DESCRIPTION
    track.is_active = True
    track.is_premium = True
    track.ordering = 1
    track.price = BACKEND_AI_TRACK_PRICE_EGP
    track.currency = "EGP"
    session.flush()

    modules = session.scalars(
        select(TrackModule)
        .where(TrackModule.track_id == track.id)
        .order_by(TrackModule.ordering, TrackModule.id)
    ).all()
    module_by_order: dict[int, TrackModule] = {}
    for module in modules:
        if (
            1 <= module.ordering <= len(CURRICULUM)
            and module.ordering not in module_by_order
        ):
            module_by_order[module.ordering] = module
        else:
            module.is_active = False

    lessons_added = 0
    assignments_added = 0
    for module_order, module_data in enumerate(CURRICULUM, start=1):
        module = module_by_order.get(module_order)
        if module is None:
            module = TrackModule(
                track_id=track.id,
                title=module_data["title"],
                description=module_data["description"],
                ordering=module_order,
                is_active=True,
            )
            session.add(module)
            session.flush()
            module_by_order[module_order] = module

        module.title = module_data["title"]
        module.description = module_data["description"]
        module.ordering = module_order
        module.is_active = True

        lessons_by_order = {
            lesson.ordering: lesson
            for lesson in session.scalars(
                select(Lesson).where(Lesson.module_id == module.id)
            ).all()
        }
        for lesson_order, lesson_data in enumerate(module_data["lessons"], start=1):
            if isinstance(lesson_data, dict):
                lesson_title = lesson_data["title"]
                lesson_description = lesson_data["description"]
                lesson_content = lesson_data.get("content") or lesson_description
                lesson_video_url = lesson_data.get("video_url")
                preserve_existing_content = module_order == 1
            else:
                lesson_title, lesson_content = lesson_data
                lesson_description = lesson_content
                lesson_video_url = None
                preserve_existing_content = False

            lesson = lessons_by_order.get(lesson_order)
            if lesson is None:
                lesson = Lesson(module_id=module.id, ordering=lesson_order)
                session.add(lesson)
                lessons_added += 1
            lesson.title = lesson_title
            lesson.description = lesson_description
            if not preserve_existing_content or not lesson.content:
                lesson.content = lesson_content
            if lesson_video_url:
                lesson.video_url = lesson_video_url
            lesson.ordering = lesson_order

        assignment_data = module_data["assignment"]
        assignment = session.scalar(
            select(Assignment).where(
                Assignment.module_id == module.id,
                Assignment.ordering == 1,
            )
        )
        if assignment is None:
            assignment = Assignment(
                track_id=track.id,
                module_id=module.id,
                ordering=1,
            )
            session.add(assignment)
            assignments_added += 1
        assignment.track_id = track.id
        assignment.module_id = module.id
        assignment.lesson_id = None
        assignment.title = assignment_data["title"]
        assignment.description = assignment_data["description"]
        assignment.instructions = assignment_data["instructions"]
        assignment.difficulty = assignment_data["difficulty"]
        assignment.ordering = 1
        assignment.is_mandatory = True
        assignment.is_active = True
        assignment.estimated_minutes = assignment_data["estimated_minutes"]
        assignment.evaluation_config = {
            "criteria": [
                {"name": "Functional correctness", "weight": 40},
                {"name": "Tests and failure handling", "weight": 25},
                {"name": "Security and data integrity", "weight": 20},
                {"name": "Documentation and trade-offs", "weight": 15},
            ],
            "passing_score": 70,
        }

    session.flush()
    return track, len(CURRICULUM), lessons_added, assignments_added


def main() -> None:
    with SessionLocal() as session:
        with session.begin():
            track, module_count, lessons_added, assignments_added = (
                seed_backend_ai_track(session)
            )
        print(
            f"Seeded '{track.name}' (id={track.id}, price={track.price} EGP): "
            f"{module_count} modules, {lessons_added} new lessons, "
            f"{assignments_added} new assignments."
        )


if __name__ == "__main__":
    main()