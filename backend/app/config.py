"""Application configuration loaded from environment variables."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "change-me-to-a-random-secret-key"
    APP_NAME: str = "Lower-AIGC"
    APP_URL: str = "http://localhost:5173"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/lower_aigc.db"

    # DeepSeek API
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"

    # Email (SMTP)
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "noreply@example.com"
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@example.com"
    SMTP_USE_TLS: bool = True

    # Auth
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REQUIRE_EMAIL_VERIFICATION: bool = True

    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 16
    MAX_PARAGRAPHS_PER_DOC: int = 500


settings = Settings()
