from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.database.models import User
from learnwords.keyboards.main_menu import get_main_menu_keyboard, HELP_TEXTS, CANCEL_TEXTS
from learnwords.database.repositories.achievement_repo import AchievementRepository

router = Router(name="common_start")


@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext, user: User, is_admin: bool, session: AsyncSession):
    await state.clear()

    # Seed default achievements if needed
    ach_repo = AchievementRepository(session)
    await ach_repo.seed_default_achievements()

    welcome_text = (
        f"Здравствуйте, <b>{message.from_user.first_name or 'друг'}</b>.\n\n"
        f"Добро пожаловать в <b>LearnWords</b> — персональный преподаватель английского языка.\n\n"
        f"<b>Возможности:</b>\n"
        f"• Индивидуальный подбор слов под уровень (A1–C2) и темы\n"
        f"• Интерактивные тесты с проверкой ответов через ИИ\n"
        f"• Интервальное повторение по алгоритму SM-2\n"
        f"• Импорт слов из текста, PDF, DOCX, XLSX\n"
        f"• Статистика успеваемости и геймификация\n\n"
        f"Выберите раздел в меню ниже, чтобы начать:"
    )

    await message.answer(
        text=welcome_text,
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        parse_mode="HTML",
    )


@router.message(F.text.in_(HELP_TEXTS))
@router.message(Command("help"))
async def handle_help(message: Message, is_admin: bool):
    help_text = (
        "<b>Справка LearnWords</b>\n\n"
        "<b>Изучать слова</b> — запуск сессии изучения новых слов и мини-тестирования.\n"
        "<b>Повторение</b> — повторение ранее изученных слов по алгоритму SM-2.\n"
        "<b>Словари</b> — персональные коллекции слов, избранное и экспорт (TXT, CSV).\n"
        "<b>Импорт</b> — загрузка собственных списков из текста, PDF, DOCX или Excel.\n"
        "<b>Прогресс</b> — детальная аналитика точности ответов и динамика серий.\n"
        "<b>Настройки</b> — уровень CEFR, темы, цель по количеству слов и язык подсказок.\n"
        "<b>Достижения</b> — шкала опыта (XP), уровень и открытые награды.\n\n"
        "<i>Для отмены текущего действия отправьте «Отмена» или /cancel.</i>"
    )
    await message.answer(
        text=help_text,
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        parse_mode="HTML",
    )


@router.message(F.text.in_(CANCEL_TEXTS))
@router.message(Command("cancel"))
async def handle_cancel(message: Message, state: FSMContext, is_admin: bool):
    await state.clear()
    await message.answer(
        "Действие отменено. Главное меню:",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
    )


@router.callback_query(F.data == "noop")
async def handle_noop(callback: CallbackQuery):
    await callback.answer()
