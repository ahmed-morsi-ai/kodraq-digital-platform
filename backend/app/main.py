from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin_dashboard import (
    router as admin_dashboard_router,
    versioned_activation_router,
)
from app.api.v1.api import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(admin_dashboard_router)
app.include_router(versioned_activation_router)
