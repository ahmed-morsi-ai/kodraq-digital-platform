from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from pydantic import PositiveInt

_INSECURE_DEFAULT_SECRET_KEY = "super-secret-key-change-in-production-1234567890"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Kodraq Digital Bootcamp Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    STORAGE_LOCAL_ROOT: Path = (
        Path(__file__).resolve().parents[2] / "uploads" / "private"
    )
    SUBMISSION_MAX_FILE_BYTES: PositiveInt = 10 * 1024 * 1024
    SUBMISSION_MAX_FILES: PositiveInt = 10

    DATABASE_URL: str = (
        "postgresql://kodraq_user:kodraq_secure_password@localhost:5432/kodraq_db"
    )
    SECRET_KEY: str = _INSECURE_DEFAULT_SECRET_KEY
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    GEMINI_API_KEY: str = ""
    AI_DEFAULT_PROVIDER: str = "gemini"
    AI_DEFAULT_MODEL: str = "gemini-3.8-flash"
    AI_TIMEOUT_SECONDS: float = 30.0
    AI_MAX_RETRIES: int = 2

    # Configurable CORS origins for development and production
    BACKEND_CORS_ORIGINS: list[str | AnyHttpUrl] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list | str):
            return v
        raise ValueError(v)

    @model_validator(mode="after")
    def require_production_secret(self) -> "Settings":
        if not self.DEBUG and self.SECRET_KEY == _INSECURE_DEFAULT_SECRET_KEY:
            raise ValueError("SECRET_KEY must be configured when DEBUG is false")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
        hide_input_in_errors=True,
    )


settings = Settings()
