import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from learnwords.database.models import User, UserStatus
from learnwords.keyboards.admin import (
    get_broadcast_confirmation_keyboard,
    get_admin_panel_keyboard,
)
from learnwords.keyboards.main_menu import get_cancel_keyboard
from learnwords.states.admin_states import AdminState
from learnwords.utils.logger import logger

router = Router(name="admin_broadcast")


@router.callback_query(F.data == "adm_broadcast")
async def handle_broadcast_prompt(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return

    await state.set_state(AdminState.waiting_broadcast_message)
    await callback.message.answer(
        "<b>Рассылка сообщений ученикам</b>\n\n"
        "Введите текст сообщения для всех активных пользователей бота (поддерживается HTML):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminState.waiting_broadcast_message)
async def handle_broadcast_preview(message: Message, state: FSMContext, is_admin: bool):
    text = message.text.strip()
    await state.update_data(broadcast_text=text)

    preview_text = (
        "<b>Предпросмотр сообщения рассылки:</b>\n"
        "────────────────────────\n"
        f"{text}\n"
        "────────────────────────\n\n"
        "Отправить сообщение всем ученикам?"
    )

    await message.answer(
        text=preview_text,
        reply_markup=get_broadcast_confirmation_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "adm_broadcast_send")
async def handle_broadcast_send(callback: CallbackQuery, state: FSMContext, is_admin: bool, session: AsyncSession, bot: Bot):
    if not is_admin:
        return

    data = await state.get_data()
    broadcast_text = data.get("broadcast_text")
    await state.clear()

    if not broadcast_text:
        await callback.message.edit_text("Текст рассылки не найден.", reply_markup=get_admin_panel_keyboard())
        return

    stmt = select(User.telegram_id).where(User.status == UserStatus.ACTIVE)
    result = await session.execute(stmt)
    user_ids = list(result.scalars().all())

    sent_count = 0
    failed_count = 0

    status_msg = await callback.message.edit_text(f"Отправка рассылки для {len(user_ids)} пользователей...")

    for tg_id in user_ids:
        try:
            await bot.send_message(chat_id=tg_id, text=broadcast_text, parse_mode="HTML")
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed_count += 1
            logger.debug(f"Broadcast to {tg_id} failed: {e}")

    await status_msg.edit_text(
        f"<b>Рассылка завершена</b>\n\n"
        f"• Доставлено: <b>{sent_count}</b>\n"
        f"• Ошибок: <b>{failed_count}</b>",
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "adm_broadcast_cancel")
async def handle_broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Рассылка отменена.", reply_markup=get_admin_panel_keyboard())
    await callback.answer()
