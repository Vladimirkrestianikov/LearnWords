from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from learnwords.database.models import Dictionary


def get_dictionaries_list_keyboard(dictionaries: List[Dictionary]) -> InlineKeyboardMarkup:
    buttons = []
    for d in dictionaries:
        buttons.append([
            InlineKeyboardButton(
                text=d.title,
                callback_data=f"dict_view:{d.id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="Создать новый словарь", callback_data="dict_create")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_dictionary_detail_keyboard(dictionary_id: int, is_favorites: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Слова", callback_data=f"dict_words:{dictionary_id}:0"),
            InlineKeyboardButton(text="Поиск", callback_data=f"dict_search:{dictionary_id}"),
        ],
        [
            InlineKeyboardButton(text="Добавить слово", callback_data=f"dict_add_word:{dictionary_id}"),
            InlineKeyboardButton(text="Тест", callback_data=f"dict_quiz:{dictionary_id}"),
        ],
        [
            InlineKeyboardButton(text="Экспорт TXT", callback_data=f"dict_export_txt:{dictionary_id}"),
            InlineKeyboardButton(text="Экспорт CSV", callback_data=f"dict_export_csv:{dictionary_id}"),
        ],
    ]
    if not is_favorites:
        buttons.append([
            InlineKeyboardButton(text="Удалить словарь", callback_data=f"dict_delete:{dictionary_id}")
        ])
    buttons.append([
        InlineKeyboardButton(text="К списку словарей", callback_data="dict_list")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_words_pagination_keyboard(dictionary_id: int, page: int, total_pages: int) -> InlineKeyboardMarkup:
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="← Назад", callback_data=f"dict_words:{dictionary_id}:{page-1}"))
    row.append(InlineKeyboardButton(text=f"{page+1}/{max(1, total_pages)}", callback_data="noop"))
    if page < total_pages - 1:
        row.append(InlineKeyboardButton(text="Вперед →", callback_data=f"dict_words:{dictionary_id}:{page+1}"))

    buttons = [
        row,
        [InlineKeyboardButton(text="Назад к словарю", callback_data=f"dict_view:{dictionary_id}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
