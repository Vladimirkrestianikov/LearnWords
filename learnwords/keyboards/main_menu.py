from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

# Main menu labels. Old labels (with emoji / long names) are still accepted by the
# handlers so users with a cached keyboard keep working after the update.
BTN_LEARN = "Изучать слова"
BTN_REVIEW = "Повторение"
BTN_DICTS = "Словари"
BTN_IMPORT = "Импорт"
BTN_PROGRESS = "Прогресс"
BTN_ACHIEVEMENTS = "Достижения"
BTN_SETTINGS = "Настройки"
BTN_HELP = "Помощь"
BTN_ADMIN = "Админ-панель"
BTN_CANCEL = "Отмена"

LEARN_TEXTS = [BTN_LEARN, "📚 Изучать слова"]
REVIEW_TEXTS = [BTN_REVIEW, "🔄 Повторение"]
DICTS_TEXTS = [BTN_DICTS, "Мои словари", "🧠 Мои словари"]
IMPORT_TEXTS = [BTN_IMPORT, "Импорт слов", "📥 Импорт слов"]
PROGRESS_TEXTS = [BTN_PROGRESS, "Мой прогресс", "📊 Мой прогресс"]
ACHIEVEMENTS_TEXTS = [BTN_ACHIEVEMENTS, "🏆 Достижения"]
SETTINGS_TEXTS = [BTN_SETTINGS, "⚙️ Настройки"]
HELP_TEXTS = [BTN_HELP, "❓ Помощь"]
ADMIN_TEXTS = [BTN_ADMIN, "🛡 Админ-панель"]
CANCEL_TEXTS = [BTN_CANCEL, "❌ Отмена"]


def get_main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Compact 3-row main menu: the two main actions on top, the rest below."""
    keyboard = [
        [
            KeyboardButton(text=BTN_LEARN),
            KeyboardButton(text=BTN_REVIEW),
        ],
        [
            KeyboardButton(text=BTN_DICTS),
            KeyboardButton(text=BTN_IMPORT),
            KeyboardButton(text=BTN_PROGRESS),
        ],
        [
            KeyboardButton(text=BTN_ACHIEVEMENTS),
            KeyboardButton(text=BTN_SETTINGS),
            KeyboardButton(text=BTN_HELP),
        ],
    ]

    if is_admin:
        keyboard.append([KeyboardButton(text=BTN_ADMIN)])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        # Not persistent: the user can collapse the menu with the keyboard icon.
        is_persistent=False,
    )


def get_remove_keyboard() -> ReplyKeyboardRemove:
    """Hides the bottom ReplyKeyboardMarkup during learning/testing."""
    return ReplyKeyboardRemove()


async def hide_main_menu(message: Message, text: str = "Подготовка...") -> Message:
    """
    Hide the bottom menu and return a fresh message to put inline content into.

    Telegram does not let a message that was sent with ReplyKeyboardRemove get an
    inline keyboard later via edit, so the service message is deleted and a new,
    plain message is returned for the card/question.
    """
    service_msg = await message.answer(text, reply_markup=ReplyKeyboardRemove())
    try:
        await service_msg.delete()
    except Exception:
        pass
    return await message.answer(text)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Minimalist cancel keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
    )
