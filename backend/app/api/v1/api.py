from fastapi import APIRouter

from app.api.v1 import health, login, users

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
