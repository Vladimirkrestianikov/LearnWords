from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_word_card_keyboard(word_id: int, is_favorite: bool = False) -> InlineKeyboardMarkup:
    """
    Two short rows so the card text stays the main thing on screen.
    Row 1: mark the word (know / hard / favorite)
    Row 2: actions (test / finish / next) - "next" sits bottom-right under the thumb
    """
    fav_symbol = "★" if is_favorite else "☆"
    buttons = [
        [
            InlineKeyboardButton(text="Знаю", callback_data=f"learn_know:{word_id}"),
            InlineKeyboardButton(text="Сложное", callback_data=f"learn_hard:{word_id}"),
            InlineKeyboardButton(text=fav_symbol, callback_data=f"learn_fav:{word_id}"),
        ],
        [
            InlineKeyboardButton(text="Тест", callback_data=f"learn_test:{word_id}"),
            InlineKeyboardButton(text="Завершить", callback_data="learn_finish"),
            InlineKeyboardButton(text="Далее →", callback_data=f"learn_next:{word_id}"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_text_answer_keyboard(word_id: int, single_mode: bool = False) -> InlineKeyboardMarkup:
    """One row under questions that expect a typed answer."""
    if single_mode:
        row = [InlineKeyboardButton(text="← К карточке", callback_data="learn_back")]
    else:
        row = [
            InlineKeyboardButton(text="Пропустить", callback_data=f"quiz_skip:{word_id}"),
            InlineKeyboardButton(text="Завершить", callback_data="learn_finish"),
        ]
    return InlineKeyboardMarkup(inline_keyboard=[row])


def get_choice_test_keyboard(options: List[str], word_id: int, single_mode: bool = False) -> InlineKeyboardMarkup:
    """Minimalist multiple-choice options."""
    buttons = []
    letters = ["A", "B", "C", "D"]
    for i, opt in enumerate(options[:4]):
        letter = letters[i] if i < len(letters) else str(i + 1)
        buttons.append([
            InlineKeyboardButton(
                text=f"{letter}. {opt}",
                callback_data=f"quiz_choice:{word_id}:{i}"
            )
        ])
    buttons.append(get_text_answer_keyboard(word_id, single_mode).inline_keyboard[0])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_test_feedback_keyboard(word_id: int, next_exists: bool = True, single_mode: bool = False) -> InlineKeyboardMarkup:
    """Minimalist feedback navigation."""
    if single_mode:
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="← К карточке", callback_data="learn_back"),
        ]])
    row = []
    if next_exists:
        row.append(InlineKeyboardButton(text="Далее →", callback_data="quiz_next"))
    row.append(InlineKeyboardButton(text="Завершить", callback_data="learn_finish"))
    return InlineKeyboardMarkup(inline_keyboard=[row])


def get_review_hub_keyboard(counts: dict) -> InlineKeyboardMarkup:
    """Minimalist review actions."""
    due_count = counts.get("due", 0)
    diff_count = counts.get("difficult", 0)
    buttons = [
        [
            InlineKeyboardButton(
                text=f"Повторить слова ({due_count})",
                callback_data="review_start_due"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"Сложные слова ({diff_count})",
                callback_data="review_start_difficult"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
