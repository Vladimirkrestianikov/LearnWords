from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.config.settings import settings
from learnwords.database.repositories.admin_repo import AdminRepository
from learnwords.keyboards.admin import get_ai_settings_keyboard

router = Router(name="admin_ai_settings")


@router.callback_query(F.data == "adm_ai")
async def handle_admin_ai_menu(callback: CallbackQuery, is_admin: bool, session: AsyncSession):
    if not is_admin:
        return

    admin_repo = AdminRepository(session)
    active_model = await admin_repo.get_system_setting("OPENAI_MODEL", default=settings.OPENAI_MODEL)

    text = (
        "<b>Настройки OpenAI API</b>\n\n"
        f"Текущая активная модель: <code>{active_model}</code>\n"
        f"API Key: <code>sk-proj-**** (защищен)</code>\n\n"
        "<i>Выберите модель для генерации слов и проверки ответов:</i>"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_ai_settings_keyboard(active_model),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_set_model:"))
async def handle_admin_set_model(callback: CallbackQuery, is_admin: bool, session: AsyncSession):
    if not is_admin:
        return

    new_model = callback.data.split(":")[1]
    admin_repo = AdminRepository(session)
    await admin_repo.set_system_setting("OPENAI_MODEL", new_model, description="Active OpenAI Model")

    await callback.answer(f"Модель изменена на {new_model}!", show_alert=True)
    await handle_admin_ai_menu(callback, is_admin, session)

