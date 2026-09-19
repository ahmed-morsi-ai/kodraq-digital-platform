from fastapi import APIRouter

from app.api.v1 import (
    assignments,
    enrollments,
    final_projects,
    health,
    login,
    quizzes,
    submissions,
    tracks,
    users,
)

api_router = APIRouter()

api_router.include_router(
    login.router,
    tags=["login"],
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"],
)

api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"],
)

api_router.include_router(
    tracks.router,
    prefix="/tracks",
    tags=["tracks"],
)

api_router.include_router(
    enrollments.router,
    prefix="/enrollments",
    tags=["enrollments"],
)

api_router.include_router(
    assignments.router,
    prefix="/assignments",
    tags=["assignments"],
)

api_router.include_router(
    submissions.router,
    prefix="/submissions",
    tags=["submissions"],
)

api_router.include_router(
    submissions.assignment_submissions_router,
    prefix="/assignments",
    tags=["submissions"],
)

api_router.include_router(
    quizzes.router,
    prefix="/quizzes",
    tags=["quizzes"],
)

api_router.include_router(
    quizzes.attempt_router,
    prefix="/quiz-attempts",
    tags=["quiz-attempts"],
)

api_router.include_router(
    final_projects.router,
    prefix="/final-projects",
    tags=["final-projects"],
)
