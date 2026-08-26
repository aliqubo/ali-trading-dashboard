"""Application configuration.

Central settings source for the whole backend. All configuration is read from
environment variables via Pydantic Settings (ARCHITECTURE.md §10, BACKEND_SPEC §7.4).

No hardcoded configuration values are allowed elsewhere in the codebase; every
component receives settings through dependency injection.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvName = Literal["development", "staging", "production", "test"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Insecure default values that must never be used in production. If any of these
# is still in place while ENVIRONMENT=production, the application fails fast on
# startup (BACKEND_SPEC §8.11 / §10, ARCHITECTURE.md §10).
DEFAULT_POSTGRES_PASSWORD = "ali_password"  # noqa: S105 (documented default)
DEFAULT_POSTGRES_USER = "ali"
DEFAULT_JWT_SECRET_KEY = "insecure-development-only-secret-change-me"  # noqa: S105


class Settings(BaseSettings):
    """Strongly-typed application settings.

    The application should fail fast on startup if a mandatory setting is
    missing (BACKEND_SPEC §10 / ARCHITECTURE.md §10).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "Ali Trading Dashboard"
    app_version: str = "1.0.0"
    environment: EnvName = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Logging ---
    log_level: LogLevel = "INFO"
    log_json: bool = True

    # --- CORS ---
    cors_origins: list[str] = Field(default_factory=list)

    # --- Database (PostgreSQL) ---
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = DEFAULT_POSTGRES_USER
    postgres_password: str = DEFAULT_POSTGRES_PASSWORD
    postgres_db: str = "ali_trading"
    database_pool_size: int = 10
    database_max_overflow: int = 5

    # --- Redis ---
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0

    # --- JWT / Token Infrastructure (Phase 3.3) ---
    # All values configurable via environment; no secret is hardcoded in
    # business logic — only this documented, fail-fast-protected development
    # default (mirrors DEFAULT_POSTGRES_PASSWORD above).
    jwt_secret_key: str = DEFAULT_JWT_SECRET_KEY
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30
    jwt_issuer: str = "ali-trading-dashboard"
    jwt_audience: str = "ali-trading-dashboard-clients"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, value: object) -> object:
        """Allow a comma-separated string for CORS origins in env files."""
        if isinstance(value, str):
            if not value.strip():
                return []
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _enforce_production_secrets(self) -> Settings:
        """Fail fast if insecure defaults are used in production.

        In a production environment, leaving the documented default database
        credentials in place is a security risk. The application must refuse to
        start with a clear message rather than run with weak secrets
        (BACKEND_SPEC §8.11 / §10).
        """
        if self.environment != "production":
            return self

        insecure: list[str] = []
        if self.postgres_password == DEFAULT_POSTGRES_PASSWORD:
            insecure.append("POSTGRES_PASSWORD")
        if self.postgres_user == DEFAULT_POSTGRES_USER:
            insecure.append("POSTGRES_USER")
        if self.jwt_secret_key == DEFAULT_JWT_SECRET_KEY:
            insecure.append("JWT_SECRET_KEY")

        if insecure:
            joined = ", ".join(insecure)
            raise ValueError(
                "Insecure default credentials detected in production for: "
                f"{joined}. Set explicit, non-default values via environment "
                "variables before starting in production."
            )
        return self

    @property
    def database_url(self) -> str:
        """Async SQLAlchemy database URL."""
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                port=self.postgres_port,
                path=self.postgres_db,
            )
        )

    @property
    def alembic_database_url(self) -> str:
        """Synchronous URL for Alembic migrations."""
        return str(
            PostgresDsn.build(
                scheme="postgresql+psycopg",
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                port=self.postgres_port,
                path=self.postgres_db,
            )
        )

    @property
    def redis_url(self) -> str:
        """Redis connection URL."""
        return str(
            RedisDsn.build(
                scheme="redis",
                host=self.redis_host,
                port=self.redis_port,
                path=str(self.redis_db),
            )
        )

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached so the environment is parsed once per process. Injected everywhere
    via dependency injection rather than imported ad hoc.
    """
    return Settings()
