from functools import lru_cache
from urllib.parse import quote

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(..., alias="BOT_TOKEN")

    # Postgres credentials — the single source of truth for the DB connection.
    # The async and Alembic URLs are derived from these (see properties below),
    # so the password is defined in exactly one place.
    postgres_user: str = Field("crypto_bot", alias="POSTGRES_USER")
    postgres_password: str = Field("change_me_strong_password", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field("crypto_discipline", alias="POSTGRES_DB")
    postgres_host: str = Field("db", alias="POSTGRES_HOST")
    postgres_port: int = Field(5432, alias="POSTGRES_PORT")

    # Optional full-URL overrides. Leave empty to build the URLs from the
    # POSTGRES_* fields above; set them only for a non-standard connection.
    database_url_override: str = Field("", alias="DATABASE_URL")
    alembic_database_url_override: str = Field("", alias="ALEMBIC_DATABASE_URL")

    openai_api_key: str = Field("", alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o-mini", alias="OPENAI_MODEL")
    anthropic_api_key: str = Field("", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field("claude-3-5-sonnet-latest", alias="ANTHROPIC_MODEL")

    ollama_base_url: str = Field("", alias="OLLAMA_BASE_URL")
    ollama_model_coach: str = Field("llama3.1:8b", alias="OLLAMA_MODEL_COACH")
    ollama_model_officer: str = Field("llama3.1:8b", alias="OLLAMA_MODEL_OFFICER")

    api_host: str = Field("0.0.0.0", alias="API_HOST")
    api_port: int = Field(8000, alias="API_PORT")

    signal_bot_url: str = Field(
        "http://host.docker.internal:8765",
        alias="SIGNAL_BOT_URL",
    )

    default_max_risk_percent: float = Field(1.0, alias="DEFAULT_MAX_RISK_PERCENT")
    default_max_leverage: int = Field(5, alias="DEFAULT_MAX_LEVERAGE")
    default_min_rr: float = Field(2.0, alias="DEFAULT_MIN_RR")
    default_daily_loss_limit: float = Field(2.0, alias="DEFAULT_DAILY_LOSS_LIMIT")

    log_level: str = Field("INFO", alias="LOG_LEVEL")

    def _dsn(self, driver: str) -> str:
        password = quote(self.postgres_password, safe="")
        return (
            f"postgresql+{driver}://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url(self) -> str:
        """Async SQLAlchemy DSN (asyncpg), or the explicit override if set."""
        return self.database_url_override or self._dsn("asyncpg")

    @property
    def alembic_database_url(self) -> str:
        """Sync DSN for Alembic (psycopg2), or the explicit override if set."""
        return self.alembic_database_url_override or self._dsn("psycopg2")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
