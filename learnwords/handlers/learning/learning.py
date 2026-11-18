from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.database.models import User
from learnwords.database.repositories.word_repo import WordRepository
from learnwords.database.repositories.progress_repo import ProgressRepository
from learnwords.database.repositories.lesson_repo import LessonRepository
from learnwords.services.learning_service import LearningService
from learnwords.keyboards.learning import get_word_card_keyboard
from learnwords.keyboards.main_menu import LEARN_TEXTS, get_main_menu_keyboard, hide_main_menu
from learnwords.states.learning_states import LearningState

router = Router(name="learning_main")


@router.message(F.text.in_(LEARN_TEXTS))
async def handle_start_learning(message: Message, state: FSMContext, user: User, session: AsyncSession):
    # Hide the bottom menu so the card is not squeezed by buttons
    loading_msg = await hide_main_menu(message, "Подбираю слова...")

    learning_service = LearningService(session)
    progress_repo = ProgressRepository(session)

    try:
        lesson, words = await learning_service.start_lesson(user.id)
        if not words:
            await loading_msg.edit_text("Не удалось подобрать слова. Попробуйте позже.")
            return

        first_word = words[0]
        prog = await progress_repo.get_progress(user.id, first_word.id)
        is_fav = prog.is_favorite if prog else False

        word_ids = [w.id for w in words]
        await state.set_state(LearningState.studying_card)
        await state.update_data(
            lesson_id=lesson.id,
            word_ids=word_ids,
            current_index=0,
            test_queue=word_ids.copy(),
        )

        card_text = await learning_service.format_word_card(
            word=first_word,
            index=1,
            total=len(words),
            is_favorite=is_fav,
        )

        await loading_msg.edit_text(
            text=card_text,
            reply_markup=get_word_card_keyboard(first_word.id, is_favorite=is_fav),
            parse_mode="HTML",
        )
    except Exception as e:
        await loading_msg.edit_text(f"Ошибка при подготовке урока: {e}")


@router.callback_query(F.data.startswith("learn_next:"))
async def handle_learn_next_card(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession):
    data = await state.get_data()
    word_ids = data.get("word_ids", [])
    current_index = data.get("current_index", 0) + 1

    learning_service = LearningService(session)
    word_repo = WordRepository(session)
    progress_repo = ProgressRepository(session)

    if current_index >= len(word_ids):
        # All cards examined -> Launch testing
        from learnwords.handlers.learning.practice import launch_quiz_session
        await launch_quiz_session(callback, state, session, user)
        return

    await state.update_data(current_index=current_index)
    word_id = word_ids[current_index]
    word = await word_repo.get_by_id(word_id)
    if not word:
        await callback.answer("Слово не найдено.")
        return

    prog = await progress_repo.get_progress(user.id, word.id)
    is_fav = prog.is_favorite if prog else False

    card_text = await learning_service.format_word_card(
        word=word,
        index=current_index + 1,
        total=len(word_ids),
        is_favorite=is_fav,
    )

    await callback.message.edit_text(
        text=card_text,
        reply_markup=get_word_card_keyboard(word.id, is_favorite=is_fav),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("learn_fav:"))
async def handle_learn_toggle_fav(callback: CallbackQuery, user: User, session: AsyncSession):
    word_id = int(callback.data.split(":")[1])
    progress_repo = ProgressRepository(session)
    new_fav = await progress_repo.toggle_favorite(user.id, word_id)

    status_str = "добавлено в избранное" if new_fav else "удалено из избранного"
    await callback.answer(f"Слово {status_str}")

    await callback.message.edit_reply_markup(
        reply_markup=get_word_card_keyboard(word_id, is_favorite=new_fav)
    )


@router.callback_query(F.data.startswith("learn_know:"))
async def handle_learn_already_know(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession):
    word_id = int(callback.data.split(":")[1])
    progress_repo = ProgressRepository(session)
    await progress_repo.mark_as_known(user.id, word_id)
    await callback.answer("Отмечено как известное")

    await handle_learn_next_card(callback, state, user, session)


@router.callback_query(F.data.startswith("learn_hard:"))
async def handle_learn_hard_word(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession):
    word_id = int(callback.data.split(":")[1])
    progress_repo = ProgressRepository(session)
    await progress_repo.mark_as_difficult(user.id, word_id)
    await callback.answer("Добавлено в список сложных")

    await handle_learn_next_card(callback, state, user, session)


@router.callback_query(F.data.startswith("learn_test:"))
async def handle_learn_test_single(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession):
    word_id = int(callback.data.split(":")[1])
    from learnwords.handlers.learning.practice import present_single_word_test
    await present_single_word_test(callback, state, session, user, word_id)


@router.callback_query(F.data == "learn_back")
async def handle_learn_back_to_card(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession):
    """Return from a single-word self-test to the same card, keeping the lesson quiz queue."""
    data = await state.get_data()
    word_ids = data.get("word_ids", [])
    current_index = data.get("current_index", 0)
    if not word_ids or current_index >= len(word_ids):
        await callback.answer("Урок уже завершён.", show_alert=True)
        return

    await state.set_state(LearningState.studying_card)
    await state.update_data(
        single_mode=False,
        test_queue=data.get("saved_test_queue", word_ids.copy()),
    )

    word = await WordRepository(session).get_by_id(word_ids[current_index])
    if not word:
        await callback.answer("Слово не найдено.")
        return
    prog = await ProgressRepository(session).get_progress(user.id, word.id)
    is_fav = prog.is_favorite if prog else False

    card_text = await LearningService(session).format_word_card(
        word=word,
        index=current_index + 1,
        total=len(word_ids),
        is_favorite=is_fav,
    )
    await callback.message.edit_text(
        text=card_text,
        reply_markup=get_word_card_keyboard(word.id, is_favorite=is_fav),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "learn_finish")
async def handle_learn_finish(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession, is_admin: bool = False):
    data = await state.get_data()
    lesson_id = data.get("lesson_id")
    lesson_repo = LessonRepository(session)

    lesson = None
    if lesson_id:
        lesson = await lesson_repo.complete_lesson(lesson_id)

    await state.clear()

    summary_text = "<b>Урок завершен</b>\n\n"
    if lesson:
        summary_text += (
            f"Верно: <b>{lesson.correct_answers}</b>\n"
            f"Ошибок: <b>{lesson.incorrect_answers}</b>\n\n"
        )
    summary_text += "Слова добавлены в цикл интервального повторения."

    # Delete or edit message, then restore bottom ReplyKeyboardMarkup
    await callback.message.delete()
    await callback.message.answer(
        text=summary_text,
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        parse_mode="HTML",
    )
    await callback.answer()
