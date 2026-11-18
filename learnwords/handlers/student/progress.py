from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.keyboards.main_menu import PROGRESS_TEXTS
from learnwords.database.models import User
from learnwords.services.statistics_service import StatisticsService
from learnwords.keyboards.student import get_progress_timeframe_keyboard

router = Router(name="student_progress")


@router.message(F.text.in_(PROGRESS_TEXTS))
async def handle_my_progress(message: Message, user: User, session: AsyncSession):
    stats_service = StatisticsService(session)
    # Default to all-time (0)
    text = await stats_service.format_progress_message(user.id, timeframe_days=None)
    await message.answer(
        text=text,
        reply_markup=get_progress_timeframe_keyboard(current_days=0),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("prog_tf:"))
async def handle_progress_timeframe(callback: CallbackQuery, user: User, session: AsyncSession):
    days_str = callback.data.split(":")[1]
    days = int(days_str) if days_str != "0" else None
    current_key = int(days_str)

    stats_service = StatisticsService(session)
    text = await stats_service.format_progress_message(user.id, timeframe_days=days)

    await callback.message.edit_text(
        text=text,
        reply_markup=get_progress_timeframe_keyboard(current_days=current_key),
        parse_mode="HTML",
    )
    await callback.answer()

