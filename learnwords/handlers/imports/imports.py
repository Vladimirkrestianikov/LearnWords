from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.database.models import User
from learnwords.services.import_service import ImportService
from learnwords.keyboards.imports import get_import_menu_keyboard, get_staged_import_keyboard
from learnwords.keyboards.main_menu import get_cancel_keyboard, get_main_menu_keyboard, IMPORT_TEXTS
from learnwords.states.import_states import ImportState
from learnwords.database.repositories.import_repo import ImportRepository

router = Router(name="imports_main")


@router.message(F.text.in_(IMPORT_TEXTS))
async def handle_import_menu(message: Message, user: User, session: AsyncSession):
    import_repo = ImportRepository(session)
    import_service = ImportService(session)

    pending = await import_repo.get_pending_import(user.id)
    if pending:
        summary = await import_service.get_import_preview_summary(pending.id)
        await message.answer(
            text=f"<b>Незавершенный импорт</b>\n\n{summary}",
            reply_markup=get_staged_import_keyboard(pending.id),
            parse_mode="HTML",
        )
        return

    text = (
        "<b>Импорт словарей</b>\n\n"
        "Загрузите собственный список слов любым удобным способом.\n\n"
        "ИИ автоматически:\n"
        "• Определяет часть речи и уровень CEFR\n"
        "• Исправляет опечатки и находит дубликаты\n"
        "• Создает примеры предложений\n"
        "• Помещает слова на проверку перед добавлением в словарь\n\n"
        "<i>Выберите способ импорта:</i>"
    )
    await message.answer(
        text=text,
        reply_markup=get_import_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "import_text_input")
async def handle_import_text_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ImportState.waiting_text)
    sample = (
        "Anxious — встревоженный\n"
        "Ashamed — пристыженный\n"
        "Bored — скучающий\n"
        "Confused — растерянный"
    )
    text = (
        "<b>Вставьте ваш список слов:</b>\n\n"
        "Формат может быть любым (через дефис, тире, двоеточие или перевод с новой строки).\n\n"
        f"<i>Пример:</i>\n<code>{sample}</code>\n\n"
        "Отправьте сообщение с текстом:"
    )
    await callback.message.answer(text=text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.message(ImportState.waiting_text)
async def handle_import_text_received(message: Message, state: FSMContext, user: User, session: AsyncSession):
    raw_text = message.text.strip()
    if len(raw_text) < 5:
        await message.answer("Текст слишком короткий. Отправьте список слов.")
        return

    loading = await message.answer("Анализ и структурирование слов через ИИ...")

    import_service = ImportService(session)
    imp = await import_service.stage_import_from_text(
        user_id=user.id,
        raw_text=raw_text,
        filename="Текстовый ввод",
    )

    await state.clear()
    summary = await import_service.get_import_preview_summary(imp.id)
    await loading.edit_text(
        text=summary,
        reply_markup=get_staged_import_keyboard(imp.id),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "import_file_upload")
async def handle_import_file_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ImportState.waiting_file)
    text = (
        "<b>Загрузка файла со словарем:</b>\n\n"
        "Поддерживаемые форматы: TXT, PDF, DOCX, CSV, XLSX\n\n"
        "<i>Прикрепите и отправьте документ в чат:</i>"
    )
    await callback.message.answer(text=text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.message(ImportState.waiting_file, F.document)
async def handle_import_file_received(message: Message, state: FSMContext, user: User, session: AsyncSession, bot: Bot):
    doc = message.document
    loading = await message.answer(f"Загрузка файла <code>{doc.file_name}</code>...")

    file_info = await bot.get_file(doc.file_id)
    file_bytes_stream = await bot.download_file(file_info.file_path)
    file_bytes = file_bytes_stream.read()

    await loading.edit_text("Извлечение текста и анализ ИИ...")

    import_service = ImportService(session)
    imp, err = await import_service.stage_import_from_file(
        user_id=user.id,
        file_bytes=file_bytes,
        filename=doc.file_name or "uploaded_file",
    )

    if err:
        await loading.edit_text(f"Ошибка: {err}")
        return

    await state.clear()
    summary = await import_service.get_import_preview_summary(imp.id)
    await loading.edit_text(
        text=summary,
        reply_markup=get_staged_import_keyboard(imp.id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("imp_confirm:"))
async def handle_import_confirm(callback: CallbackQuery, user: User, session: AsyncSession, is_admin: bool):
    import_id = int(callback.data.split(":")[1])
    import_service = ImportService(session)

    added_count, target_dict = await import_service.confirm_staged_import(import_id)

    text = (
        "<b>Импорт успешно подтвержден</b>\n\n"
        f"Добавлено слов: <b>{added_count}</b>\n"
        f"Целевой словарь: <b>{target_dict.title}</b>\n\n"
        "Слова доступны в разделе «Словари» и добавлены в систему обучения."
    )
    await callback.message.edit_text(text=text, parse_mode="HTML")
    await callback.answer("Слова добавлены в словарь.")


@router.callback_query(F.data.startswith("imp_cancel:"))
async def handle_import_cancel(callback: CallbackQuery, session: AsyncSession):
    import_id = int(callback.data.split(":")[1])
    import_service = ImportService(session)
    await import_service.import_repo.cancel_import(import_id)
    await callback.message.edit_text("Импорт отменен. Временные слова удалены.", parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("imp_browse:"))
async def handle_import_browse(callback: CallbackQuery, session: AsyncSession):
    import_id = int(callback.data.split(":")[1])
    import_service = ImportService(session)
    words = await import_service.import_repo.get_words(import_id)

    lines = ["<b>Список распознанных слов:</b>\n"]
    for i, w in enumerate(words[:25], start=1):
        status_tag = "" if w.status == "VALID" else f" [{w.status}]"
        lines.append(f"{i}. <b>{w.english_word}</b> — {w.translation}{status_tag}")

    if len(words) > 25:
        lines.append(f"\n... и еще {len(words)-25} слов.")

    lines.append("\n<i>Нажмите «Добавить все слова» для сохранения.</i>")

    await callback.message.edit_text(
        text="\n".join(lines),
        reply_markup=get_staged_import_keyboard(import_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("imp_reprocess:"))
async def handle_import_reprocess(callback: CallbackQuery, user: User, session: AsyncSession):
    import_id = int(callback.data.split(":")[1])
    import_service = ImportService(session)
    words = await import_service.import_repo.get_words(import_id)

    raw_text = "\n".join([f"{w.english_word} — {w.translation}" for w in words])
    await callback.message.edit_text("Повторная обработка в OpenAI...")

    imp = await import_service.stage_import_from_text(
        user_id=user.id,
        raw_text=raw_text,
        filename="Повторная обработка",
    )
    summary = await import_service.get_import_preview_summary(imp.id)
    await callback.message.edit_text(
        text=summary,
        reply_markup=get_staged_import_keyboard(imp.id),
        parse_mode="HTML",
    )
    await callback.answer()
