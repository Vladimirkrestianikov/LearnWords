from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.database.models import User
from learnwords.keyboards.admin import get_admin_panel_keyboard
from learnwords.keyboards.main_menu import get_main_menu_keyboard, ADMIN_TEXTS

router = Router(name="admin_panel")


@router.message(Command("admin"))
@router.message(F.text.in_(ADMIN_TEXTS))
async def handle_admin_entry(message: Message, user: User, is_admin: bool):
    if not is_admin:
        await message.answer("Доступ ограничен. Команда доступна только администраторам.")
        return

    text = (
        "<b>Панель администратора LearnWords</b>\n\n"
        "Управление пользователями, словарями, параметрами ИИ и рассылками."
    )
    await message.answer(text=text, reply_markup=get_admin_panel_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "adm_menu")
async def handle_admin_menu_callback(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        await callback.answer("Доступ запрещен.", show_alert=True)
        return

    text = (
        "<b>Панель администратора LearnWords</b>\n\n"
        "Управляйте пользователями, словарями, параметрами ИИ и рассылками."
    )
    await callback.message.edit_text(text=text, reply_markup=get_admin_panel_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "adm_exit")
async def handle_admin_exit(callback: CallbackQuery, is_admin: bool):
    await callback.message.delete()
    await callback.message.answer(
        "Панель администратора закрыта. Вы в главном меню.",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
    )
    await callback.answer()

