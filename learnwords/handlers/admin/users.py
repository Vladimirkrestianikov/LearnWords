import math
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.database.models import User, UserStatus, UserRole
from learnwords.database.repositories.user_repo import UserRepository
from learnwords.database.repositories.progress_repo import ProgressRepository
from learnwords.database.repositories.lesson_repo import LessonRepository
from learnwords.keyboards.admin import (
    get_admin_users_pagination_keyboard,
    get_admin_user_card_keyboard,
)
from learnwords.keyboards.main_menu import get_cancel_keyboard
from learnwords.states.admin_states import AdminState

router = Router(name="admin_users")


@router.callback_query(F.data.startswith("adm_users_list:"))
async def handle_admin_users_list(callback: CallbackQuery, is_admin: bool, session: AsyncSession):
    if not is_admin:
        await callback.answer("Доступ запрещен.", show_alert=True)
        return

    page = int(callback.data.split(":")[1])
    page_size = 8

    user_repo = UserRepository(session)
    total_users = await user_repo.count_users()
    total_pages = math.ceil(total_users / page_size) if total_users > 0 else 1

    users = await user_repo.list_users(limit=page_size, offset=page * page_size)

    lines = [f"<b>Пользователи (стр. {page+1}/{total_pages}):</b>\n"]
    for u in users:
        role_label = "[ADMIN]" if u.role == UserRole.ADMIN else "[STUDENT]"
        status_label = " [BAN]" if u.status == UserStatus.BANNED else ""
        name = u.full_name or u.username or f"ID {u.telegram_id}"
        lines.append(f"• <b>{name}</b> ({u.telegram_id}) {role_label}{status_label} — ур. {u.level}")

    lines.append("\n<i>Для перехода к пользователю используйте поиск по ID:</i>")

    await callback.message.edit_text(
        text="\n".join(lines),
        reply_markup=get_admin_users_pagination_keyboard(page, total_pages),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "adm_user_search")
async def handle_user_search_prompt(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return
    await state.set_state(AdminState.waiting_search_id)
    await callback.message.answer(
        "Введите Telegram ID пользователя для просмотра профиля:",
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminState.waiting_search_id)
async def handle_user_search_input(message: Message, state: FSMContext, session: AsyncSession, is_admin: bool):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Введите числовой Telegram ID.")
        return

    tg_id = int(text)
    user_repo = UserRepository(session)
    target_user = await user_repo.get_by_telegram_id(tg_id)

    await state.clear()
    if not target_user:
        await message.answer(f"Пользователь с Telegram ID <code>{tg_id}</code> не найден в базе данных.", parse_mode="HTML")
        return

    prog_repo = ProgressRepository(session)
    lesson_repo = LessonRepository(session)
    rc = await prog_repo.get_review_counts(target_user.id)
    perf = await lesson_repo.get_user_performance(target_user.id)

    profile_text = (
        f"<b>Профиль пользователя</b>\n\n"
        f"Имя: <b>{target_user.full_name or '—'}</b>\n"
        f"Username: @{target_user.username or '—'}\n"
        f"Telegram ID: <code>{target_user.telegram_id}</code>\n"
        f"Роль: <b>{target_user.role}</b> | Статус: <b>{target_user.status}</b>\n"
        f"Уровень: <b>{target_user.level}</b> (XP: {target_user.xp}) | Серия: <b>{target_user.streak_days} дн.</b>\n\n"
        f"<b>Статистика:</b>\n"
        f"• Изучено слов: <b>{rc['total_learned']}</b>\n"
        f"• Запомнено: <b>{rc['mastered']}</b>\n"
        f"• Уроков: <b>{perf['completed_lessons']}</b>\n"
        f"• Точность: <b>{perf['accuracy']}%</b> ({perf['correct']}/{perf['total_attempts']})\n\n"
        f"Регистрация: {target_user.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"Активность: {target_user.last_activity.strftime('%d.%m.%Y %H:%M')}"
    )

    await message.answer(
        text=profile_text,
        reply_markup=get_admin_user_card_keyboard(target_user),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("adm_user_action:"))
async def handle_admin_user_action(callback: CallbackQuery, is_admin: bool, session: AsyncSession):
    if not is_admin:
        return
    parts = callback.data.split(":")
    user_id = int(parts[1])
    action = parts[2]

    user_repo = UserRepository(session)
    target_user = await user_repo.get_by_id(user_id)
    if not target_user:
        await callback.answer("Пользователь не найден.")
        return

    if action == "ban":
        await user_repo.update_status(user_id, UserStatus.BANNED)
        await callback.answer("Пользователь заблокирован.")
    elif action == "unban":
        await user_repo.update_status(user_id, UserStatus.ACTIVE)
        await callback.answer("Пользователь разблокирован.")
    elif action == "promote":
        await user_repo.update_role(user_id, UserRole.ADMIN)
        await callback.answer("Назначен администратором.")
    elif action == "demote":
        await user_repo.update_role(user_id, UserRole.STUDENT)
        await callback.answer("Роль изменена на ученика.")

    target_user = await user_repo.get_by_id(user_id)
    await callback.message.edit_reply_markup(
        reply_markup=get_admin_user_card_keyboard(target_user)
    )


@router.callback_query(F.data.startswith("adm_user_reset_confirm:"))
async def handle_admin_user_reset(callback: CallbackQuery, is_admin: bool, session: AsyncSession):
    if not is_admin:
        return
    user_id = int(callback.data.split(":")[1])
    user_repo = UserRepository(session)
    target_user = await user_repo.get_by_id(user_id)
    if target_user:
        target_user.xp = 0
        target_user.level = 1
        target_user.streak_days = 0
        await session.commit()
        await callback.answer("Статистика пользователя сброшена.", show_alert=True)
