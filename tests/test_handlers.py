import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage, StorageKey
from learnwords.database.models import User, UserSettings, UserRole, UserStatus
from learnwords.handlers.common.start import handle_start, handle_help, handle_cancel
from learnwords.handlers.student.settings import handle_settings_menu
from learnwords.handlers.student.progress import handle_my_progress
from learnwords.handlers.dictionaries.dictionaries import handle_my_dictionaries
from learnwords.handlers.learning.review import handle_review_hub


@pytest.mark.asyncio
async def test_start_and_help_handlers(test_session):
    storage = MemoryStorage()
    key = StorageKey(bot_id=123, chat_id=111, user_id=111)
    fsm_ctx = FSMContext(storage=storage, key=key)

    mock_msg = AsyncMock()
    mock_msg.from_user = MagicMock(id=111, first_name="Alex", username="alex")
    mock_msg.answer = AsyncMock()

    user = User(
        id=1,
        telegram_id=111,
        role=UserRole.STUDENT,
        status=UserStatus.ACTIVE,
        xp=0,
        level=1,
    )

    # 1. /start
    await handle_start(mock_msg, fsm_ctx, user, is_admin=False, session=test_session)
    assert mock_msg.answer.called
    call_args = mock_msg.answer.call_args[1]
    assert "LearnWords" in call_args["text"]

    # 2. /help
    mock_msg.answer.reset_mock()
    await handle_help(mock_msg, is_admin=False)
    assert mock_msg.answer.called
    assert "Справка" in mock_msg.answer.call_args[1]["text"]

    # 3. /cancel
    mock_msg.answer.reset_mock()
    await handle_cancel(mock_msg, fsm_ctx, is_admin=False)
    assert mock_msg.answer.called
    assert "Действие отменено" in mock_msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_student_menu_handlers(test_session):
    mock_msg = AsyncMock()
    mock_msg.from_user = MagicMock(id=222, first_name="Maria")
    mock_msg.answer = AsyncMock()

    user = User(
        id=2,
        telegram_id=222,
        role=UserRole.STUDENT,
        status=UserStatus.ACTIVE,
        xp=150,
        level=2,
        streak_days=3,
    )
    user.settings = UserSettings(
        user_id=2,
        english_level="B2",
        preferred_topics='["Travel", "Food"]',
        daily_word_goal=15,
        difficulty="STANDARD",
        explanation_language="RU",
        learning_mode="NEW_WORDS",
        reminder_enabled=True,
    )
    test_session.add(user)
    await test_session.commit()

    # Settings menu
    await handle_settings_menu(mock_msg, user, test_session)
    assert mock_msg.answer.called
    assert "Параметры обучения" in mock_msg.answer.call_args[1]["text"]

    # Progress
    mock_msg.answer.reset_mock()
    await handle_my_progress(mock_msg, user, test_session)
    assert mock_msg.answer.called
    assert "Прогресс" in mock_msg.answer.call_args[1]["text"]

    # Dictionaries
    mock_msg.answer.reset_mock()
    await handle_my_dictionaries(mock_msg, user, test_session)
    assert mock_msg.answer.called
    assert "Мои словари" in mock_msg.answer.call_args[1]["text"]

    # Review hub
    mock_msg.answer.reset_mock()
    await handle_review_hub(mock_msg, user, test_session)
    assert mock_msg.answer.called
    assert "Интервальное повторение" in mock_msg.answer.call_args[1]["text"]

