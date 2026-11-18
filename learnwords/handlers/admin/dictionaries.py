from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from learnwords.database.models import Dictionary
from learnwords.database.repositories.dictionary_repo import DictionaryRepository
from learnwords.keyboards.admin import get_admin_panel_keyboard
from learnwords.keyboards.main_menu import get_cancel_keyboard
from learnwords.states.admin_states import AdminState

router = Router(name="admin_dictionaries")


@router.callback_query(F.data == "adm_dicts")
async def handle_admin_dictionaries(callback: CallbackQuery, is_admin: bool, session: AsyncSession):
    if not is_admin:
        return

    stmt = select(Dictionary).where(Dictionary.is_public == True)
    result = await session.execute(stmt)
    public_dicts = list(result.scalars().all())

    lines = ["<b>Общие словари (доступны всем ученикам):</b>\n"]
    if not public_dicts:
        lines.append("<i>Пока нет созданных системных словарей.</i>")
    else:
        for i, d in enumerate(public_dicts, start=1):
            lines.append(f"{i}. <b>{d.title}</b> (ID: {d.id})")

    buttons = [
        [InlineKeyboardButton(text="Создать общий словарь", callback_data="adm_create_public_dict")],
        [InlineKeyboardButton(text="В админ-панель", callback_data="adm_menu")],
    ]

    await callback.message.edit_text(
        text="\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "adm_create_public_dict")
async def handle_create_public_dict_prompt(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return

    await state.set_state(AdminState.waiting_dict_title)
    await callback.message.answer(
        "Введите название для общего словаря (например, <i>Top 500 Oxford Words</i>):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminState.waiting_dict_title)
async def handle_create_public_dict_title(message: Message, state: FSMContext, session: AsyncSession, is_admin: bool):
    title = message.text.strip()
    dict_repo = DictionaryRepository(session)
    d = await dict_repo.create_dictionary(
        title=title,
        user_id=None,
        description="Общедоступный словарь от кураторов LearnWords",
        dictionary_type="SYSTEM",
        is_public=True,
    )
    await state.clear()
    await message.answer(
        f"Общий словарь <b>«{d.title}»</b> успешно создан и опубликован для всех учеников.",
        parse_mode="HTML",
    )
