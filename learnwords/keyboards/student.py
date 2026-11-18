from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from learnwords.database.models import UserSettings


AVAILABLE_TOPICS = [
    ("Everyday Life", "Повседневная жизнь"),
    ("Emotions", "Чувства и эмоции"),
    ("Relationships", "Отношения"),
    ("Cars", "Автомобили"),
    ("Technology", "Технологии"),
    ("Business", "Бизнес"),
    ("Work", "Работа"),
    ("Travel", "Путешествия"),
    ("Food", "Еда"),
    ("Education", "Образование"),
    ("Personality", "Характер"),
    ("Health", "Здоровье"),
    ("Internet & Gaming", "Интернет и игры"),
    ("Phrasal Verbs", "Фразовые глаголы"),
    ("Common Expressions", "Распространенные выражения"),
    ("Custom Topic", "Своя тема"),
]


def get_settings_menu_keyboard(settings: UserSettings) -> InlineKeyboardMarkup:
    rem_status = "Вкл" if settings.reminder_enabled else "Выкл"
    buttons = [
        [
            InlineKeyboardButton(
                text=f"Уровень: {settings.english_level}",
                callback_data="set_menu_level"
            ),
            InlineKeyboardButton(
                text=f"Цель: {settings.daily_word_goal} слов",
                callback_data="set_menu_goal"
            ),
        ],
        [
            InlineKeyboardButton(
                text="Тема обучения",
                callback_data="set_menu_topic"
            ),
            InlineKeyboardButton(
                text=f"Сложность: {settings.difficulty}",
                callback_data="set_menu_diff"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Язык: {settings.explanation_language}",
                callback_data="set_menu_lang"
            ),
            InlineKeyboardButton(
                text=f"Режим: {settings.learning_mode}",
                callback_data="set_menu_mode"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Напоминания: {rem_status}",
                callback_data="set_toggle_reminder"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_level_selection_keyboard(current_level: str) -> InlineKeyboardMarkup:
    levels = [
        ("A1", "A1 — Beginner"),
        ("A2", "A2 — Elementary"),
        ("B1", "B1 — Intermediate"),
        ("B2", "B2 — Upper-Intermediate"),
        ("C1", "C1 — Advanced"),
        ("C2", "C2 — Proficiency"),
    ]
    buttons = []
    for code, title in levels:
        mark = "✓ " if code == current_level else ""
        buttons.append([
            InlineKeyboardButton(text=f"{mark}{title}", callback_data=f"set_val_level:{code}")
        ])
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="set_menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_topic_selection_keyboard(current_topics: list) -> InlineKeyboardMarkup:
    buttons = []
    for code, label in AVAILABLE_TOPICS:
        mark = "✓ " if code in current_topics else ""
        buttons.append([
            InlineKeyboardButton(text=f"{mark}{label}", callback_data=f"set_val_topic:{code}")
        ])
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="set_menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_goal_selection_keyboard(current_goal: int) -> InlineKeyboardMarkup:
    goals = [5, 10, 15, 20, 30]
    row = []
    for g in goals:
        mark = "✓" if g == current_goal else ""
        row.append(InlineKeyboardButton(text=f"{mark}{g}", callback_data=f"set_val_goal:{g}"))
    buttons = [
        row,
        [InlineKeyboardButton(text="Свой вариант", callback_data="set_custom_goal")],
        [InlineKeyboardButton(text="Назад", callback_data="set_menu_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_difficulty_selection_keyboard(current_diff: str) -> InlineKeyboardMarkup:
    diffs = [
        ("EASY", "Легкая"),
        ("STANDARD", "Стандартная"),
        ("INTENSIVE", "Интенсивная"),
    ]
    buttons = []
    for code, label in diffs:
        mark = "✓ " if code == current_diff else ""
        buttons.append([
            InlineKeyboardButton(text=f"{mark}{label}", callback_data=f"set_val_diff:{code}")
        ])
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="set_menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_language_selection_keyboard(current_lang: str) -> InlineKeyboardMarkup:
    langs = [
        ("RU", "Русский"),
        ("EN", "Английский"),
        ("MIXED", "Смешанный"),
    ]
    buttons = []
    for code, label in langs:
        mark = "✓ " if code == current_lang else ""
        buttons.append([
            InlineKeyboardButton(text=f"{mark}{label}", callback_data=f"set_val_lang:{code}")
        ])
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="set_menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_mode_selection_keyboard(current_mode: str) -> InlineKeyboardMarkup:
    modes = [
        ("NEW_WORDS", "Изучение новых слов"),
        ("INTENSIVE", "Интенсивное запоминание"),
        ("TESTING_ONLY", "Только тестирование"),
        ("REVIEW_FORGOTTEN", "Повторение забытых"),
        ("SENTENCE_PRACTICE", "Практика предложений"),
    ]
    buttons = []
    for code, label in modes:
        mark = "✓ " if code == current_mode else ""
        buttons.append([
            InlineKeyboardButton(text=f"{mark}{label}", callback_data=f"set_val_mode:{code}")
        ])
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="set_menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_progress_timeframe_keyboard(current_days: int) -> InlineKeyboardMarkup:
    timeframes = [
        (1, "Сегодня"),
        (7, "7 дней"),
        (30, "30 дней"),
        (0, "Все время"),
    ]
    row = []
    for d, title in timeframes:
        mark = "• " if d == current_days else ""
        row.append(InlineKeyboardButton(text=f"{mark}{title}", callback_data=f"prog_tf:{d}"))
    return InlineKeyboardMarkup(inline_keyboard=[row])
