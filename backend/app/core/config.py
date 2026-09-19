"""Environment-backed application settings."""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Supported runtime environments."""

    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Validated runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Supply Chain Disruption Autopilot"
    app_version: str = "0.1.0"
    environment: Environment = Environment.DEVELOPMENT
    demo_mode: bool = True
    log_level: str = "INFO"
    database_url: str = Field(
        default="postgresql+asyncpg://supply_chain:change-me-for-local-development@localhost:5432/supply_chain"
    )
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000"
    ai_provider: str = "mock"
    ai_model: str = "gpt-4.1-mini"
    openai_api_key: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        """Return normalized origins without accepting a wildcard with credentials."""

        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings instance per process."""

    return Settings()
