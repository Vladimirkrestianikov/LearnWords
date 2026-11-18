from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.database.repositories.admin_repo import AdminRepository
from learnwords.keyboards.admin import get_admin_panel_keyboard

router = Router(name="admin_stats")


@router.callback_query(F.data == "adm_stats")
async def handle_admin_global_stats(callback: CallbackQuery, is_admin: bool, session: AsyncSession):
    if not is_admin:
        await callback.answer("Доступ запрещен.")
        return

    admin_repo = AdminRepository(session)
    stats = await admin_repo.get_global_stats()

    text = (
        "<b>Общая статистика LearnWords</b>\n\n"
        f"Всего пользователей: <b>{stats['total_users']}</b>\n"
        f"Новых за 24 часа: <b>{stats['new_users_24h']}</b>\n"
        f"Активных за 7 дней: <b>{stats['active_users_7d']}</b>\n"
        f"Заблокировано: <b>{stats['banned_users']}</b>\n\n"
        f"Слов в базе данных: <b>{stats['total_words']}</b>\n"
        f"Завершено уроков: <b>{stats['total_lessons']}</b>\n"
        f"Проведено тестов: <b>{stats['total_tests']}</b>\n"
        f"Общая точность ответов: <b>{stats['overall_accuracy']}%</b>\n\n"
        f"Сессий импорта: <b>{stats['total_imports']}</b>\n"
        f"Обращений к OpenAI API: <b>{stats['ai_calls']}</b>"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "adm_logs")
async def handle_admin_logs(callback: CallbackQuery, is_admin: bool, session: AsyncSession):
    if not is_admin:
        return

    admin_repo = AdminRepository(session)
    logs = await admin_repo.get_recent_logs(limit=12)

    lines = ["<b>Последние системные события:</b>\n"]
    if not logs:
        lines.append("<i>Логи пусты</i>")
    else:
        for log in logs:
            time_str = log.created_at.strftime("%H:%M:%S")
            user_part = f" [User {log.user_id}]" if log.user_id else ""
            lines.append(f"• <code>{time_str}</code> <b>{log.action}</b>{user_part}: {log.details or '—'}")

    await callback.message.edit_text(
        text="\n".join(lines),
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()
