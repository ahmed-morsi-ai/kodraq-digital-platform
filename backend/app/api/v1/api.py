from fastapi import APIRouter

from app.api.v1 import enrollments, health, login, tracks, users

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
