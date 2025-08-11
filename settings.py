from functools import lru_cache
from typing import Optional

from pydantic import AliasChoices, Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _build_postgres_dsn(
    *,
    user: str,
    password: str,
    host: str,
    port: int,
    database: str,
) -> str:
    """
    Construct an async SQLAlchemy-compatible Postgres DSN using asyncpg.
    Example: postgresql+asyncpg://user:password@host:5432/dbname
    """
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"


class Settings(BaseSettings):
    """Application settings loaded from environment variables and optional .env files.

    Priority order (highest first): env vars > .env > .env.postgres > defaults.

    Exposes a resolved Postgres URL, conversation history limit, and default thread title.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.postgres"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database URL can be provided directly. If not provided, it's built from parts below.
    database_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "POSTGRES_URL", "PG_DSN"),
        description="Full Postgres SQLAlchemy URL (prefer async: postgresql+asyncpg://...)",
    )

    # Individual Postgres components (used only when database_url is not set)
    postgres_user: Optional[str] = Field(default=None, validation_alias=AliasChoices("POSTGRES_USER", "PGUSER"))
    postgres_password: Optional[str] = Field(default=None, validation_alias=AliasChoices("POSTGRES_PASSWORD", "PGPASSWORD"))
    postgres_db: Optional[str] = Field(default=None, validation_alias=AliasChoices("POSTGRES_DB", "PGDATABASE"))
    postgres_host: str = Field(default="localhost", validation_alias=AliasChoices("POSTGRES_HOST", "PGHOST"))
    postgres_port: int = Field(default=5432, validation_alias=AliasChoices("POSTGRES_PORT", "PGPORT"))

    # AI agent conversation settings
    ai_history_limit: int = Field(
        default=20,
        validation_alias=AliasChoices("AI_HISTORY_LIMIT", "HISTORY_LIMIT"),
        description="Max number of prior messages to include in the agent conversation context.",
    )

    # Default title to use for new threads
    thread_title: str = Field(
        default="Chat",
        validation_alias=AliasChoices("THREAD_TITLE", "DEFAULT_THREAD_TITLE"),
        description="Default title for a conversation thread if none is supplied by the client.",
    )

    @field_validator("ai_history_limit")
    @classmethod
    def _validate_history_limit(cls, value: int) -> int:
        if value < 0:
            raise ValueError("AI history limit must be >= 0")
        return value

    @computed_field(return_type=str)  # type: ignore[valid-type]
    @property
    def resolved_database_url(self) -> str:
        """Return a valid Postgres DSN, building from parts if needed.

        Raises ValidationError if insufficient components are present to build a URL.
        """
        if self.database_url:
            # Basic validation for acceptable schemes
            allowed_prefixes = ("postgresql://", "postgres://", "postgresql+asyncpg://")
            if not any(self.database_url.startswith(prefix) for prefix in allowed_prefixes):
                raise ValueError(
                    "DATABASE_URL must start with one of: postgresql://, postgres://, postgresql+asyncpg://"
                )
            return self.database_url

        missing_parts = [
            name
            for name, value in (
                ("POSTGRES_USER", self.postgres_user),
                ("POSTGRES_PASSWORD", self.postgres_password),
                ("POSTGRES_DB", self.postgres_db),
            )
            if not value
        ]
        if missing_parts:
            raise ValueError(
                f"DATABASE_URL not set and required components missing: {', '.join(missing_parts)}"
            )

        built = _build_postgres_dsn(
            user=self.postgres_user or "",  # validated above
            password=self.postgres_password or "",
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db or "",
        )
        return built


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton-ish accessor so we only read/parse env once per process."""
    return Settings()  # type: ignore[call-arg]


# Convenience instance for simple imports: from settings import settings
settings = get_settings()


