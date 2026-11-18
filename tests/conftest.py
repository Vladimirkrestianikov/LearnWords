import pytest
import pytest_asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from learnwords.database.database import Base
from learnwords.database.repositories.user_repo import UserRepository
from learnwords.database.repositories.settings_repo import SettingsRepository
from learnwords.database.repositories.word_repo import WordRepository
from learnwords.database.repositories.dictionary_repo import DictionaryRepository
from learnwords.database.repositories.progress_repo import ProgressRepository
from learnwords.database.repositories.lesson_repo import LessonRepository
from learnwords.database.repositories.import_repo import ImportRepository
from learnwords.database.repositories.achievement_repo import AchievementRepository
from learnwords.database.repositories.admin_repo import AdminRepository


@pytest_asyncio.fixture(scope="function")
async def test_session():
    # In-memory SQLite async engine for tests
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

