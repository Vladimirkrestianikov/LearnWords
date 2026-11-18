from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from learnwords.database.models import User, UserStatus, UserRole


def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Пользователи", callback_data="adm_users_list:0"),
            InlineKeyboardButton(text="Статистика", callback_data="adm_stats"),
        ],
        [
            InlineKeyboardButton(text="Общие словари", callback_data="adm_dicts"),
            InlineKeyboardButton(text="Настройки ИИ", callback_data="adm_ai"),
        ],
        [
            InlineKeyboardButton(text="Рассылка", callback_data="adm_broadcast"),
            InlineKeyboardButton(text="Логи и события", callback_data="adm_logs"),
        ],
        [
            InlineKeyboardButton(text="Закрыть панель", callback_data="adm_exit"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_user_card_keyboard(target_user: User) -> InlineKeyboardMarkup:
    ban_label = "Разблокировать" if target_user.status == UserStatus.BANNED else "Заблокировать"
    ban_action = "unban" if target_user.status == UserStatus.BANNED else "ban"

    role_label = "Сделать учеником" if target_user.role == UserRole.ADMIN else "Назначить админом"
    role_action = "demote" if target_user.role == UserRole.ADMIN else "promote"

    buttons = [
        [
            InlineKeyboardButton(text=ban_label, callback_data=f"adm_user_action:{target_user.id}:{ban_action}"),
            InlineKeyboardButton(text=role_label, callback_data=f"adm_user_action:{target_user.id}:{role_action}"),
        ],
        [
            InlineKeyboardButton(text="Сбросить статистику", callback_data=f"adm_user_reset_confirm:{target_user.id}"),
        ],
        [
            InlineKeyboardButton(text="Назад к списку", callback_data="adm_users_list:0"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_users_pagination_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="← Назад", callback_data=f"adm_users_list:{page-1}"))
    row.append(InlineKeyboardButton(text=f"{page+1}/{max(1, total_pages)}", callback_data="noop"))
    if page < total_pages - 1:
        row.append(InlineKeyboardButton(text="Вперед →", callback_data=f"adm_users_list:{page+1}"))

    buttons = [
        row,
        [InlineKeyboardButton(text="Поиск по Telegram ID", callback_data="adm_user_search")],
        [InlineKeyboardButton(text="В админ-панель", callback_data="adm_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_ai_settings_keyboard(current_model: str) -> InlineKeyboardMarkup:
    models = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
    buttons = []
    for m in models:
        mark = "✓ " if m == current_model else ""
        buttons.append([
            InlineKeyboardButton(text=f"{mark}{m}", callback_data=f"adm_set_model:{m}")
        ])
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="adm_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_broadcast_confirmation_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Отправить", callback_data="adm_broadcast_send"),
            InlineKeyboardButton(text="Отмена", callback_data="adm_broadcast_cancel"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
