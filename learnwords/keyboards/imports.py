from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_import_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Вставить текст", callback_data="import_text_input"),
        ],
        [
            InlineKeyboardButton(text="Загрузить файл (TXT, DOCX, PDF, CSV, XLSX)", callback_data="import_file_upload"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_staged_import_keyboard(import_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Добавить все слова", callback_data=f"imp_confirm:{import_id}"),
        ],
        [
            InlineKeyboardButton(text="Просмотреть список", callback_data=f"imp_browse:{import_id}"),
            InlineKeyboardButton(text="Обработать заново", callback_data=f"imp_reprocess:{import_id}"),
        ],
        [
            InlineKeyboardButton(text="Отменить импорт", callback_data=f"imp_cancel:{import_id}"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
