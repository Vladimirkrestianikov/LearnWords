import os
from pathlib import Path
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)
from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase
from learnwords.config.settings import settings
from learnwords.utils.logger import logger


class Base(DeclarativeBase):
    pass


# Ensure data directory exists if local sqlite path is used
if "sqlite" in settings.DATABASE_URL:
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable SQLite WAL mode, foreign keys, and busy timeout for concurrent safety."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
    except Exception as e:
        logger.warning(f"Error setting SQLite PRAGMA: {e}")
    finally:
        cursor.close()


async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables in database if they don't exist."""
    from learnwords.database import models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully.")


async def close_db() -> None:
    """Dispose of engine connections."""
    await engine.dispose()
    logger.info("Database connection closed.")

