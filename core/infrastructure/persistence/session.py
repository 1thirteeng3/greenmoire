from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.infrastructure.persistence.settings import (
    DatabaseSettings,
    load_database_settings,
)


def create_engine(settings: DatabaseSettings | None = None) -> AsyncEngine:
    db_settings = settings or load_database_settings()
    return create_async_engine(
        db_settings.async_database_url,
        echo=db_settings.sql_echo,
        future=True,
        pool_pre_ping=True,
    )


def create_session_factory(
    engine: AsyncEngine | None = None,
) -> async_sessionmaker[AsyncSession]:
    async_engine = engine or create_engine()
    return async_sessionmaker(
        bind=async_engine, expire_on_commit=False, class_=AsyncSession
    )


@asynccontextmanager
async def session_scope(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> AsyncIterator[AsyncSession]:
    factory = session_factory or create_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
