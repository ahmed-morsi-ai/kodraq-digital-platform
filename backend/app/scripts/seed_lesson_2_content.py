from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.session import SessionLocal
from app.models.track import Lesson, Track, TrackModule

TRACK_SLUG = "backend-ai-engineering"
MODULE_TITLE = "Module 0: Backend Mindset & Architecture"
LESSON_TITLE = "The Complete Request/Response Lifecycle"
LESSON_ORDERING = 2
LESSON_DESCRIPTION = (
    "Trace an HTTP request end-to-end: from client DNS and reverse proxy through "
    "ASGI server routing, Pydantic validation, auth guards, DB transactions, "
    "and serialized JSON responses."
)
VIDEO_URL = "https://www.youtube.com/embed/tLzM-QQvvUo"

LESSON_CONTENT = """# Lesson 2: The Complete Request/Response Lifecycle

Tracing a request from the moment a user interacts with a client application to the database transaction and back is the foundational skill required to debug, optimize latency, and secure backend systems.

---

### 1. Client Initiation & Transport Layer

1. **DNS Lookup:**
    The browser converts the domain name (e.g., `api.kodraq.com`) to an IP address using local DNS caches or recursive DNS resolution.

2. **TCP Handshake & TLS 1.3:**
    * **TCP 3-Way Handshake:** Establishes connection reliability via `SYN`, `SYN-ACK`, and `ACK` packets.
    * **TLS Encryption:** Encrypts data payload using TLS handshakes to prevent Man-in-the-Middle eavesdropping.

3. **HTTP Request Anatomy:**
    * **Start Line:** `POST /api/v1/enrollments HTTP/1.1`
    * **Headers:** Metadata like `Host`, `Content-Type: application/json`, and `Authorization: Bearer <token>`.
    * **Body:** JSON payload containing client input data.

---

### 2. Reverse Proxy & Edge Gateway Layer

Before touching Python/FastAPI, requests pass through a Reverse Proxy (e.g., **Nginx** or **Traefik**):

* **SSL Termination:** Decrypts incoming HTTPS traffic at the edge and proxies unencrypted internal HTTP to the local app runner.
* **Rate Limiting & DDoS Protection:** Filters request frequencies per IP to prevent service flooding.
* **CORS Preflight:** Automatically intercepts browser `OPTIONS` preflight requests and appends `Access-Control-Allow-Origin` headers.

---

### 3. ASGI Server & FastAPI Pipeline

```text
[Client] -> [Nginx/Traefik] -> [Uvicorn (ASGI)] -> [Middleware Stack] -> [FastAPI Router] -> [Pydantic/Auth] -> [DB Transaction]
```

1. **ASGI Runner (Uvicorn):**
    Converts network HTTP bytes into standard Python ASGI scope dictionaries, enabling asynchronous I/O (`async/await`).

2. **Middleware Pipeline:**
    Applies sequential request handlers:
    * **Correlation ID Middleware:** Attaches a unique `X-Request-ID` to trace logs across distributed services.
    * **Compression & CORS Middleware:** Handles payload compression and cross-origin headers.

3. **Routing:**
    FastAPI matches path and method (`POST /api/v1/enrollments`) to delegate execution to the designated route handler function.

---

### 4. Validation, Auth & Business Logic

1. **Pydantic Data Validation:**
    Parses raw JSON into Pydantic models. Malformed types or missing required fields trigger an immediate `422 Unprocessable Entity` response.

2. **Dependency Injection & Auth Guards:**
    Executes `Depends(get_current_user)` to decode and verify JWT signatures, enforce role permissions, and inject the authenticated user instance.

3. **Business Logic Execution:**
    Evaluates domain rules (e.g., seat availability, duplicate enrollment prevention).

---

### 5. Persistence & Response Serialization

1. **Unit of Work & DB Transactions:**
    * Opens a SQLAlchemy session (`SessionLocal()`).
    * Executes database queries inside an atomic transaction block.
    * **Commit:** Persists state changes on success.
    * **Rollback:** Reverts all operations on failure to guarantee database consistency (ACID compliance).

2. **Response Serialization & Status Codes:**
    * `200 OK`: Successful read or update.
    * `201 Created`: Successful resource creation.
    * `401 Unauthorized`: Missing or invalid JWT credentials.
    * `422 Unprocessable Entity`: Validation failure.
    * `500 Internal Server Error`: Unhandled server exception.

FastAPI serializes the resulting Pydantic/SQLAlchemy objects into JSON string format for HTTP client consumption.
"""

LESSON_QUIZ_DATA = [
    {
        "id": 1,
        "question": "Which component is responsible for SSL Termination and Rate Limiting before requests reach FastAPI?",
        "options": [
            "Database Driver (SQLAlchemy)",
            "Reverse Proxy / Edge Gateway (e.g., Nginx or Traefik)",
            "Frontend Browser Client",
            "Pydantic Validation Schema",
        ],
        "correct_index": 1,
        "explanation": "A Reverse Proxy sits at the edge of the network to handle SSL decryption, DDoS protection, and rate limiting before forwarding traffic to Uvicorn.",
    },
    {
        "id": 2,
        "question": "What HTTP status code does FastAPI automatically return when a request payload fails Pydantic validation?",
        "options": [
            "200 OK",
            "401 Unauthorized",
            "422 Unprocessable Entity",
            "500 Internal Server Error",
        ],
        "correct_index": 2,
        "explanation": "Pydantic validation failures trigger an immediate 422 Unprocessable Entity HTTP response containing specific parameter error details.",
    },
    {
        "id": 3,
        "question": "Why is a Database Rollback executed if an exception occurs during business logic?",
        "options": [
            "To improve client network speed.",
            "To prevent partial corrupted writes and maintain Database ACID consistency.",
            "To clear browser cache.",
            "To refresh JWT tokens.",
        ],
        "correct_index": 1,
        "explanation": "Rollbacks ensure that failed transactions leave no partial or corrupt state changes in PostgreSQL, preserving system integrity.",
    },
]


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
                Lesson.ordering == LESSON_ORDERING,
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
            or persisted_lesson.ordering != LESSON_ORDERING
            or persisted_lesson.description != LESSON_DESCRIPTION
            or persisted_lesson.content != LESSON_CONTENT
            or persisted_lesson.video_url != VIDEO_URL
            or persisted_lesson.quiz_data != LESSON_QUIZ_DATA
        ):
            raise RuntimeError("Lesson 2 content did not persist as expected")
        print(
            f"Updated lesson {persisted_lesson.id}: {persisted_lesson.title} "
            f"({len(LESSON_CONTENT)} characters, {len(LESSON_QUIZ_DATA)} quiz questions)."
        )


if __name__ == "__main__":
    main()