import math
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.database.models import User
from learnwords.database.repositories.dictionary_repo import DictionaryRepository
from learnwords.database.repositories.word_repo import WordRepository
from learnwords.services.vocabulary_service import VocabularyService
from learnwords.keyboards.dictionaries import (
    get_dictionaries_list_keyboard,
    get_dictionary_detail_keyboard,
    get_words_pagination_keyboard,
)
from learnwords.keyboards.main_menu import get_cancel_keyboard, get_main_menu_keyboard, hide_main_menu, DICTS_TEXTS
from learnwords.states.dictionary_states import DictionaryState
from learnwords.states.learning_states import LearningState
from learnwords.handlers.learning.practice import present_next_quiz_item

router = Router(name="dictionaries_main")


@router.message(F.text.in_(DICTS_TEXTS))
async def handle_my_dictionaries(message: Message, user: User, session: AsyncSession):
    dict_repo = DictionaryRepository(session)
    await dict_repo.get_or_create_favorites(user.id)
    user_dicts = await dict_repo.get_user_dictionaries(user.id)

    lines = ["<b>Мои словари</b>\n"]
    for i, d in enumerate(user_dicts, start=1):
        count = await dict_repo.count_words_in_dictionary(d.id)
        lines.append(f"{i}. <b>{d.title}</b> — {count} слов")

    text = "\n".join(lines) + "\n\n<i>Выберите словарь:</i>"
    await message.answer(
        text=text,
        reply_markup=get_dictionaries_list_keyboard(user_dicts),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "dict_list")
async def handle_dict_list_callback(callback: CallbackQuery, user: User, session: AsyncSession):
    dict_repo = DictionaryRepository(session)
    user_dicts = await dict_repo.get_user_dictionaries(user.id)

    lines = ["<b>Мои словари</b>\n"]
    for i, d in enumerate(user_dicts, start=1):
        count = await dict_repo.count_words_in_dictionary(d.id)
        lines.append(f"{i}. <b>{d.title}</b> — {count} слов")

    text = "\n".join(lines) + "\n\n<i>Выберите словарь:</i>"
    await callback.message.edit_text(
        text=text,
        reply_markup=get_dictionaries_list_keyboard(user_dicts),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "dict_create")
async def handle_dict_create(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DictionaryState.waiting_title)
    await callback.message.answer(
        "Введите название нового словаря (например, <i>Business English</i>):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(DictionaryState.waiting_title)
async def handle_dict_title_input(message: Message, user: User, state: FSMContext, session: AsyncSession, is_admin: bool):
    title = message.text.strip()
    if not title or len(title) > 80:
        await message.answer("Пожалуйста, введите корректное название словаря (до 80 символов).")
        return

    dict_repo = DictionaryRepository(session)
    new_dict = await dict_repo.create_dictionary(
        title=title,
        user_id=user.id,
        dictionary_type="USER",
    )
    await state.clear()
    await message.answer(
        f"Словарь <b>«{new_dict.title}»</b> успешно создан.",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("dict_view:"))
async def handle_dict_view(callback: CallbackQuery, user: User, session: AsyncSession):
    dict_id = int(callback.data.split(":")[1])
    dict_repo = DictionaryRepository(session)
    d = await dict_repo.get_by_id(dict_id)
    if not d:
        await callback.answer("Словарь не найден.")
        return

    count = await dict_repo.count_words_in_dictionary(dict_id)
    desc = f"\nОписание: {d.description}" if d.description else ""
    text = (
        f"Словарь: <b>{d.title}</b>{desc}\n"
        f"Всего слов: <b>{count}</b>\n\n"
        "<i>Выберите действие:</i>"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_dictionary_detail_keyboard(d.id, is_favorites=(d.dictionary_type == "FAVORITES")),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dict_words:"))
async def handle_dict_words_pagination(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    dict_id = int(parts[1])
    page = int(parts[2])

    page_size = 10
    dict_repo = DictionaryRepository(session)
    total_words = await dict_repo.count_words_in_dictionary(dict_id)
    total_pages = math.ceil(total_words / page_size) if total_words > 0 else 1

    words = await dict_repo.get_words_in_dictionary(dict_id, limit=page_size, offset=page * page_size)

    lines = [f"<b>Слова в словаре (стр. {page+1}/{total_pages}):</b>\n"]
    if not words:
        lines.append("<i>Словарь пока пуст. Вы можете добавить слова вручную или импортировать их.</i>")
    else:
        for i, w in enumerate(words, start=page * page_size + 1):
            pos = f" ({w.part_of_speech})" if w.part_of_speech else ""
            lines.append(f"{i}. <b>{w.english_word}</b> — {w.translation}{pos}")

    await callback.message.edit_text(
        text="\n".join(lines),
        reply_markup=get_words_pagination_keyboard(dict_id, page, total_pages),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dict_search:"))
async def handle_dict_search_prompt(callback: CallbackQuery, state: FSMContext):
    dict_id = int(callback.data.split(":")[1])
    await state.set_state(DictionaryState.waiting_search_query)
    await state.update_data(active_dict_id=dict_id)
    await callback.message.answer(
        "Введите слово или часть слова для поиска (на английском или русском):",
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(DictionaryState.waiting_search_query)
async def handle_dict_search_query(message: Message, state: FSMContext, session: AsyncSession, is_admin: bool):
    query = message.text.strip()
    data = await state.get_data()
    dict_id = data.get("active_dict_id")

    word_repo = WordRepository(session)
    matches = await word_repo.search_words(query, limit=10)

    await state.clear()
    if not matches:
        await message.answer(
            f"По запросу <i>«{query}»</i> ничего не найдено.",
            reply_markup=get_main_menu_keyboard(is_admin=is_admin),
            parse_mode="HTML",
        )
        return

    lines = [f"<b>Результаты поиска по «{query}»:</b>\n"]
    for w in matches:
        lines.append(f"• <b>{w.english_word}</b> — {w.translation} [{w.cefr_level or 'B1'}]")

    await message.answer(
        text="\n".join(lines),
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("dict_add_word:"))
async def handle_dict_manual_add(callback: CallbackQuery, state: FSMContext):
    dict_id = int(callback.data.split(":")[1])
    await state.set_state(DictionaryState.waiting_word_english)
    await state.update_data(active_dict_id=dict_id)
    await callback.message.answer(
        "Введите слово или фразу на <b>английском языке</b>:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(DictionaryState.waiting_word_english)
async def handle_manual_word_en(message: Message, state: FSMContext):
    en_word = message.text.strip()
    await state.update_data(manual_en=en_word)
    await state.set_state(DictionaryState.waiting_word_translation)
    await message.answer(
        f"Введите перевод для слова <b>«{en_word}»</b> на русский язык:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(DictionaryState.waiting_word_translation)
async def handle_manual_word_ru(message: Message, state: FSMContext, session: AsyncSession, is_admin: bool):
    ru_trans = message.text.strip()
    data = await state.get_data()
    en_word = data.get("manual_en")
    dict_id = data.get("active_dict_id")

    word_repo = WordRepository(session)
    dict_repo = DictionaryRepository(session)

    word = await word_repo.get_or_create_word(
        english_word=en_word,
        translation=ru_trans,
    )
    if dict_id:
        await dict_repo.add_word_to_dictionary(dict_id, word.id)

    await state.clear()
    await message.answer(
        f"Слово <b>{word.english_word}</b> — <i>{word.translation}</i> успешно сохранено.",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("dict_quiz:"))
async def handle_dict_quiz(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession):
    dict_id = int(callback.data.split(":")[1])
    dict_repo = DictionaryRepository(session)
    words = await dict_repo.get_words_in_dictionary(dict_id, limit=10)

    if not words:
        await callback.answer("В этом словаре пока нет слов для теста.", show_alert=True)
        return

    word_ids = [w.id for w in words]
    await state.set_state(LearningState.answering_test)
    await state.update_data(test_queue=word_ids, lesson_id=None)

    await callback.message.delete()
    sent = await hide_main_menu(callback.message, "Запуск теста по словарю...")
    await present_next_quiz_item(sent, state, session, user)
    await callback.answer()


@router.callback_query(F.data.startswith("dict_export_txt:"))
async def handle_export_txt(callback: CallbackQuery, session: AsyncSession):
    dict_id = int(callback.data.split(":")[1])
    vocab_service = VocabularyService(session)
    text_content = await vocab_service.export_dictionary_text(dict_id)

    file_bytes = text_content.encode("utf-8")
    doc = BufferedInputFile(file_bytes, filename=f"dictionary_{dict_id}.txt")
    await callback.message.answer_document(
        document=doc,
        caption="Экспорт словаря в формате TXT",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dict_export_csv:"))
async def handle_export_csv(callback: CallbackQuery, session: AsyncSession):
    dict_id = int(callback.data.split(":")[1])
    vocab_service = VocabularyService(session)
    csv_content = await vocab_service.export_dictionary_csv(dict_id)

    file_bytes = csv_content.encode("utf-8-sig")
    doc = BufferedInputFile(file_bytes, filename=f"dictionary_{dict_id}.csv")
    await callback.message.answer_document(
        document=doc,
        caption="Экспорт словаря в формате CSV",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dict_delete:"))
async def handle_dict_delete(callback: CallbackQuery, user: User, session: AsyncSession):
    dict_id = int(callback.data.split(":")[1])
    dict_repo = DictionaryRepository(session)
    await dict_repo.delete_dictionary(dict_id)
    await callback.answer("Словарь удален.")
    await handle_dict_list_callback(callback, user, session)
