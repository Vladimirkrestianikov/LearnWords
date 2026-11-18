import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.database.models import User
from learnwords.database.repositories.settings_repo import SettingsRepository
from learnwords.keyboards.student import (
    get_settings_menu_keyboard,
    get_level_selection_keyboard,
    get_topic_selection_keyboard,
    get_goal_selection_keyboard,
    get_difficulty_selection_keyboard,
    get_language_selection_keyboard,
    get_mode_selection_keyboard,
)
from learnwords.keyboards.main_menu import get_cancel_keyboard, get_main_menu_keyboard, SETTINGS_TEXTS
from learnwords.states.settings_states import SettingsState

router = Router(name="student_settings")


@router.message(F.text.in_(SETTINGS_TEXTS))
async def handle_settings_menu(message: Message, user: User, session: AsyncSession):
    settings_repo = SettingsRepository(session)
    settings = await settings_repo.get_by_user_id(user.id)

    topics_list = settings_repo.parse_topics(settings)
    topics_str = ", ".join(topics_list) if topics_list else "Everyday Life"
    if settings.custom_topic:
        topics_str += f" (Своя: {settings.custom_topic})"

    text = (
        "<b>Параметры обучения</b>\n\n"
        f"Уровень CEFR: <b>{settings.english_level}</b>\n"
        f"Темы: <b>{topics_str}</b>\n"
        f"Дневная цель: <b>{settings.daily_word_goal} слов</b>\n"
        f"Сложность: <b>{settings.difficulty}</b>\n"
        f"Язык объяснений: <b>{settings.explanation_language}</b>\n"
        f"Режим: <b>{settings.learning_mode}</b>\n"
        f"Напоминания: <b>{'Включены' if settings.reminder_enabled else 'Выключены'}</b>\n\n"
        "<i>Выберите пункт для изменения:</i>"
    )
    await message.answer(text=text, reply_markup=get_settings_menu_keyboard(settings), parse_mode="HTML")


@router.callback_query(F.data == "set_menu_back")
async def handle_settings_back(callback: CallbackQuery, user: User, session: AsyncSession):
    settings_repo = SettingsRepository(session)
    settings = await settings_repo.get_by_user_id(user.id)
    topics_list = settings_repo.parse_topics(settings)
    topics_str = ", ".join(topics_list) if topics_list else "Everyday Life"

    text = (
        "<b>Параметры обучения</b>\n\n"
        f"Уровень CEFR: <b>{settings.english_level}</b>\n"
        f"Темы: <b>{topics_str}</b>\n"
        f"Дневная цель: <b>{settings.daily_word_goal} слов</b>\n"
        f"Сложность: <b>{settings.difficulty}</b>\n"
        f"Язык объяснений: <b>{settings.explanation_language}</b>\n"
        f"Режим: <b>{settings.learning_mode}</b>\n"
        f"Напоминания: <b>{'Включены' if settings.reminder_enabled else 'Выключены'}</b>\n\n"
        "<i>Выберите пункт для изменения:</i>"
    )
    await callback.message.edit_text(text=text, reply_markup=get_settings_menu_keyboard(settings), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "set_menu_level")
async def handle_set_menu_level(callback: CallbackQuery, user: User, session: AsyncSession):
    settings_repo = SettingsRepository(session)
    settings = await settings_repo.get_by_user_id(user.id)
    await callback.message.edit_text(
        "Выберите ваш текущий уровень владения английским языком по шкале CEFR:",
        reply_markup=get_level_selection_keyboard(settings.english_level),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_val_level:"))
async def handle_set_level_value(callback: CallbackQuery, user: User, session: AsyncSession):
    level = callback.data.split(":")[1]
    settings_repo = SettingsRepository(session)
    await settings_repo.update_settings(user.id, english_level=level)
    await callback.answer(f"Уровень изменён на {level}!")
    # Return to menu
    await handle_settings_back(callback, user, session)


@router.callback_query(F.data == "set_menu_topic")
async def handle_set_menu_topic(callback: CallbackQuery, user: User, session: AsyncSession):
    settings_repo = SettingsRepository(session)
    settings = await settings_repo.get_by_user_id(user.id)
    current_topics = settings_repo.parse_topics(settings)
    await callback.message.edit_text(
        "Выберите интересующую тематику для изучения слов:",
        reply_markup=get_topic_selection_keyboard(current_topics),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_val_topic:"))
async def handle_set_topic_value(callback: CallbackQuery, user: User, session: AsyncSession, state: FSMContext):
    topic = callback.data.split(":")[1]
    if topic == "Custom Topic":
        await state.set_state(SettingsState.waiting_custom_topic)
        await callback.message.answer(
            "Введите название вашей собственной темы (например, <i>Medical English</i> или <i>Startup Vocabulary</i>):",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    settings_repo = SettingsRepository(session)
    await settings_repo.update_settings(user.id, preferred_topics=[topic], custom_topic=None)
    await callback.answer(f"Тема установлена: {topic}")
    await handle_settings_back(callback, user, session)


@router.message(SettingsState.waiting_custom_topic)
async def handle_custom_topic_input(message: Message, user: User, state: FSMContext, session: AsyncSession, is_admin: bool):
    custom_title = message.text.strip()
    if not custom_title or len(custom_title) > 100:
        await message.answer("Пожалуйста, введите корректное название темы (до 100 символов).")
        return

    settings_repo = SettingsRepository(session)
    await settings_repo.update_settings(
        user.id,
        preferred_topics=["Custom Topic"],
        custom_topic=custom_title,
    )
    await state.clear()
    await message.answer(
        f"Тема сохранена: <b>{html.escape(custom_title)}</b>",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "set_menu_goal")
async def handle_set_menu_goal(callback: CallbackQuery, user: User, session: AsyncSession):
    settings_repo = SettingsRepository(session)
    settings = await settings_repo.get_by_user_id(user.id)
    await callback.message.edit_text(
        "Сколько новых слов в день вы хотите изучать?",
        reply_markup=get_goal_selection_keyboard(settings.daily_word_goal),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_val_goal:"))
async def handle_set_goal_value(callback: CallbackQuery, user: User, session: AsyncSession):
    goal = int(callback.data.split(":")[1])
    settings_repo = SettingsRepository(session)
    await settings_repo.update_settings(user.id, daily_word_goal=goal)
    await callback.answer(f"Цель установлена: {goal} слов в день!")
    await handle_settings_back(callback, user, session)


@router.callback_query(F.data == "set_custom_goal")
async def handle_set_custom_goal(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.waiting_custom_goal)
    await callback.message.answer(
        "Введите желаемое количество слов в день числом (от 1 до 100):",
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(SettingsState.waiting_custom_goal)
async def handle_custom_goal_input(message: Message, user: User, state: FSMContext, session: AsyncSession, is_admin: bool):
    text = message.text.strip()
    if not text.isdigit() or not (1 <= int(text) <= 100):
        await message.answer("Пожалуйста, введите целое число от 1 до 100.")
        return

    goal = int(text)
    settings_repo = SettingsRepository(session)
    await settings_repo.update_settings(user.id, daily_word_goal=goal)
    await state.clear()
    await message.answer(
        f"Цель сохранена: <b>{goal} слов в день</b>",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "set_menu_diff")
async def handle_set_menu_diff(callback: CallbackQuery, user: User, session: AsyncSession):
    settings_repo = SettingsRepository(session)
    settings = await settings_repo.get_by_user_id(user.id)
    await callback.message.edit_text(
        "Выберите темп и сложность обучения:",
        reply_markup=get_difficulty_selection_keyboard(settings.difficulty),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_val_diff:"))
async def handle_set_diff_value(callback: CallbackQuery, user: User, session: AsyncSession):
    diff = callback.data.split(":")[1]
    settings_repo = SettingsRepository(session)
    await settings_repo.update_settings(user.id, difficulty=diff)
    await callback.answer(f"Сложность: {diff}")
    await handle_settings_back(callback, user, session)


@router.callback_query(F.data == "set_menu_lang")
async def handle_set_menu_lang(callback: CallbackQuery, user: User, session: AsyncSession):
    settings_repo = SettingsRepository(session)
    settings = await settings_repo.get_by_user_id(user.id)
    await callback.message.edit_text(
        "Выберите основной язык объяснений и подсказок ИИ:",
        reply_markup=get_language_selection_keyboard(settings.explanation_language),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_val_lang:"))
async def handle_set_lang_value(callback: CallbackQuery, user: User, session: AsyncSession):
    lang = callback.data.split(":")[1]
    settings_repo = SettingsRepository(session)
    await settings_repo.update_settings(user.id, explanation_language=lang)
    await callback.answer(f"Язык объяснений: {lang}")
    await handle_settings_back(callback, user, session)


@router.callback_query(F.data == "set_menu_mode")
async def handle_set_menu_mode(callback: CallbackQuery, user: User, session: AsyncSession):
    settings_repo = SettingsRepository(session)
    settings = await settings_repo.get_by_user_id(user.id)
    await callback.message.edit_text(
        "Выберите режим учебного процесса:",
        reply_markup=get_mode_selection_keyboard(settings.learning_mode),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_val_mode:"))
async def handle_set_mode_value(callback: CallbackQuery, user: User, session: AsyncSession):
    mode = callback.data.split(":")[1]
    settings_repo = SettingsRepository(session)
    await settings_repo.update_settings(user.id, learning_mode=mode)
    await callback.answer(f"Режим обучения: {mode}")
    await handle_settings_back(callback, user, session)


@router.callback_query(F.data == "set_toggle_reminder")
async def handle_toggle_reminder(callback: CallbackQuery, user: User, session: AsyncSession):
    settings_repo = SettingsRepository(session)
    settings = await settings_repo.get_by_user_id(user.id)
    new_state = not settings.reminder_enabled
    await settings_repo.update_settings(user.id, reminder_enabled=new_state)
    status_text = "включены" if new_state else "выключены"
    await callback.answer(f"Напоминания {status_text}!")
    await handle_settings_back(callback, user, session)

