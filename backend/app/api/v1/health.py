from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("", response_model=dict[str, str])
def health_check() -> dict[str, str]:
    """
    System health check endpoint.
    """
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }
