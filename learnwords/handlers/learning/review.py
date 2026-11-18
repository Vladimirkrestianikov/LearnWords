from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.database.models import User
from learnwords.services.review_service import ReviewService
from learnwords.keyboards.learning import get_review_hub_keyboard
from learnwords.keyboards.main_menu import REVIEW_TEXTS, hide_main_menu
from learnwords.states.learning_states import LearningState
from learnwords.handlers.learning.practice import present_next_quiz_item

router = Router(name="learning_review")


@router.message(F.text.in_(REVIEW_TEXTS))
async def handle_review_hub(message: Message, user: User, session: AsyncSession):
    review_service = ReviewService(session)
    counts = await review_service.get_review_dashboard(user.id)

    text = (
        "<b>Интервальное повторение (SM-2)</b>\n\n"
        f"Ожидают повторения: <b>{counts['due']}</b>\n"
        f"Просрочено: <b>{counts['overdue']}</b>\n"
        f"В процессе изучения: <b>{counts['learning']}</b>\n"
        f"Надежно запомнено: <b>{counts['mastered']}</b>\n"
        f"Сложных слов: <b>{counts['difficult']}</b>\n\n"
        "<i>Интервальное повторение закрепляет слова в долговременной памяти.</i>"
    )

    await message.answer(
        text=text,
        reply_markup=get_review_hub_keyboard(counts),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "review_start_due")
async def handle_review_start_due(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession):
    review_service = ReviewService(session)
    words = await review_service.get_words_for_review_session(user.id, only_difficult=False, limit=10)

    if not words:
        await callback.answer("Нет слов, требующих повторения прямо сейчас.", show_alert=True)
        return

    word_ids = [w.id for w in words]
    await state.set_state(LearningState.answering_test)
    await state.update_data(
        test_queue=word_ids,
        lesson_id=None,
    )

    await callback.message.delete()
    sent = await hide_main_menu(callback.message, "Повторение слов...")
    await present_next_quiz_item(sent, state, session, user)
    await callback.answer()


@router.callback_query(F.data == "review_start_difficult")
async def handle_review_start_difficult(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession):
    review_service = ReviewService(session)
    words = await review_service.get_words_for_review_session(user.id, only_difficult=True, limit=10)

    if not words:
        await callback.answer("Сложных слов не найдено.", show_alert=True)
        return

    word_ids = [w.id for w in words]
    await state.set_state(LearningState.answering_test)
    await state.update_data(
        test_queue=word_ids,
        lesson_id=None,
    )

    await callback.message.delete()
    sent = await hide_main_menu(callback.message, "Повторение сложных слов...")
    await present_next_quiz_item(sent, state, session, user)
    await callback.answer()
