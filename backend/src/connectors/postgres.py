"""PostgreSQL connector using SQLAlchemy async engine + asyncpg."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.settings import get_settings


def create_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        future=True,
        echo=settings.environment == "local",
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )


engine = create_engine()

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_managed_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for use outside of FastAPI request lifecycle."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Cleanly close all connections. Call on application shutdown."""
    await engine.dispose()


async def initialize_database() -> None:
    """Table creation is intentionally disabled at application startup."""
    return None
