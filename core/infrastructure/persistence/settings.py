import os
from dataclasses import dataclass
from functools import lru_cache


DEFAULT_ASYNC_DATABASE_URL = (
    "postgresql+asyncpg://grimoire_admin:grimoire_secure_password@localhost:5432/grimoire_core"
)


def _to_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _derive_sync_url(async_url: str) -> str:
    if async_url.startswith("postgresql+asyncpg://"):
        return async_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if async_url.startswith("postgresql://"):
        return async_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return async_url


@dataclass(frozen=True)
class DatabaseSettings:
    async_database_url: str
    sync_database_url: str
    sql_echo: bool = False


def load_database_settings() -> DatabaseSettings:
    """
    Centraliza URLs de conexão para SQLAlchemy (async) e Alembic (sync).
    """
    async_url = os.getenv("DATABASE_URL_ASYNC")
    if not async_url:
        async_url = os.getenv("DATABASE_URL", DEFAULT_ASYNC_DATABASE_URL)

    sync_url = os.getenv("DATABASE_URL_SYNC")
    if not sync_url:
        sync_url = _derive_sync_url(async_url)

    sql_echo = _to_bool(os.getenv("SQL_ECHO"))
    return DatabaseSettings(
        async_database_url=async_url,
        sync_database_url=sync_url,
        sql_echo=sql_echo,
    )


@lru_cache(maxsize=1)
def get_database_settings() -> DatabaseSettings:
    return load_database_settings()


def build_sqlalchemy_url(*, async_mode: bool) -> str:
    settings = get_database_settings()
    return settings.async_database_url if async_mode else settings.sync_database_url
