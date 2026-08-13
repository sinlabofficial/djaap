from pathlib import Path
from typing import Any

import dj_database_url
from goodconf import Field, GoodConf

DEV_SECRET_KEY = "django-insecure-dev-key-change-in-production"
EXAMPLE_SECRET_KEY = "your-secret-key-change-this-in-production"


def csv(value: str | list[str] | tuple[str, ...] | None) -> list[str]:
    """Parse comma-separated env values while tolerating list-like defaults."""
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


def database_from_url(
    database_url: str | None,
    *,
    base_dir: Path,
    conn_max_age: int = 60,
    ssl_require: bool = False,
) -> dict[str, Any]:
    """Build Django DATABASES['default'] from DATABASE_URL with SQLite fallback."""
    url = database_url or f"sqlite:///{base_dir / 'db.sqlite3'}"
    database = dj_database_url.parse(url, conn_max_age=conn_max_age)

    engine = database.get("ENGINE", "")
    if ssl_require and engine.endswith("postgresql"):
        options = database.setdefault("OPTIONS", {})
        options.setdefault("sslmode", "require")

    return database


class Config(GoodConf):
    DEBUG: bool = Field(default=True, description="Enable debug mode")
    SECRET_KEY: str = Field(default=DEV_SECRET_KEY, description="Django secret key")
    ALLOWED_HOSTS: str = Field(
        default="localhost,127.0.0.1,testserver",
        description="Comma-separated allowed hosts",
    )
    DATABASE_URL: str = Field(default="", description="Database URL")
    DATABASE_CONN_MAX_AGE: int = Field(
        default=60, description="Database persistent connection age in seconds"
    )
    DATABASE_SSL_REQUIRE: bool = Field(
        default=False, description="Require SSL for PostgreSQL database connections"
    )
    DJANGO_ENV: str = Field(default="development", description="Environment name")
    REALTIME_ENABLED: bool = Field(
        default=False, description="Enable optional Channels realtime transport"
    )
    CHANNEL_LAYER_BACKEND: str = Field(
        default="channels.layers.InMemoryChannelLayer",
        description="Optional Channels layer adapter path",
    )
    CHANNEL_LAYER_REDIS_URL: str = Field(
        default="",
        description="Optional Redis URL for a Redis-backed Channels layer",
    )
    PLATFORM_RUNTIME_RETENTION_DAYS: int = Field(
        default=30, description="Number of days to retain runtime health records"
    )
    TASKS_BACKEND: str = Field(
        default="django.tasks.backends.immediate.ImmediateBackend",
        description="Django Tasks backend adapter for the default queue",
    )
    TASKS_WEBHOOK_BACKEND: str = Field(
        default="",
        description="Optional Django Tasks backend adapter for webhook work",
    )
    PERIODIC_SCHEDULER_ENABLED: bool = Field(
        default=False,
        description="Opt in to an externally supplied periodic scheduler",
    )
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    CORS_ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Comma-separated CORS origins",
    )
    CSRF_TRUSTED_ORIGINS: str = Field(
        default="", description="Comma-separated CSRF trusted origins"
    )
    SECURE_SSL_REDIRECT: bool = Field(
        default=True, description="Redirect HTTP to HTTPS when DEBUG=False"
    )
    SECURE_HSTS_SECONDS: int = Field(
        default=31536000, description="HSTS max age when DEBUG=False"
    )
    MIDTRANS_SERVER_KEY: str = Field(default="", description="Midtrans server key")
    MIDTRANS_CLIENT_KEY: str = Field(default="", description="Midtrans client key")


config = Config()
