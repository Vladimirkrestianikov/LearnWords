import html
from typing import Optional, List
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.database.models import User
from learnwords.database.repositories.word_repo import WordRepository
from learnwords.services.learning_service import LearningService
from learnwords.keyboards.learning import (
    get_choice_test_keyboard,
    get_test_feedback_keyboard,
    get_text_answer_keyboard,
)
from learnwords.states.learning_states import LearningState

router = Router(name="learning_practice")

# Short explanations shown under every question so the controls are self-explanatory
HINT_TYPE_ANSWER = "<b>Напишите ответ в чат обычным сообщением ↓</b>"
HINT_PICK_OPTION = "<b>Нажмите на правильный вариант ниже ↓</b>"
LEGEND_QUIZ = (
    "<i>Пропустить — следующий вопрос без ответа\n"
    "Завершить — закончить урок и посмотреть итог</i>"
)
LEGEND_SINGLE = "<i>К карточке — вернуться к слову без ответа</i>"


async def launch_quiz_session(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    """Transition from cards study to mini-quiz."""
    data = await state.get_data()
    test_queue = data.get("test_queue", [])
    if not test_queue:
        from learnwords.handlers.learning.learning import handle_learn_finish
        await handle_learn_finish(callback, state, user, session)
        return

    await state.set_state(LearningState.answering_test)
    await present_next_quiz_item(callback.message, state, session, user)


async def present_single_word_test(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User, word_id: int):
    """Direct self-test on single word from card; the lesson quiz queue is kept aside."""
    data = await state.get_data()
    await state.set_state(LearningState.answering_test)
    await state.update_data(
        saved_test_queue=data.get("test_queue", []),
        test_queue=[word_id],
        single_mode=True,
    )
    await callback.answer()
    await present_next_quiz_item(callback.message, state, session, user)


async def present_next_quiz_item(message: Message, state: FSMContext, session: AsyncSession, user: User):
    data = await state.get_data()
    test_queue = data.get("test_queue", [])
    if not test_queue:
        from learnwords.handlers.learning.learning import handle_learn_finish
        class FakeCallback:
            def __init__(self, msg):
                self.message = msg
            async def answer(self, *args, **kwargs): pass
        await handle_learn_finish(FakeCallback(message), state, user, session)
        return

    word_id = test_queue[0]
    word_repo = WordRepository(session)
    word = await word_repo.get_by_id(word_id)
    if not word:
        await state.update_data(test_queue=test_queue[1:])
        await present_next_quiz_item(message, state, session, user)
        return

    learning_service = LearningService(session)
    other_words = await word_repo.get_words_for_topic_and_level(
        topic=word.topic,
        level=word.cefr_level,
        exclude_word_ids=[word.id],
        limit=5,
    )

    q_data = await learning_service.generate_test_question(word, other_words=other_words)

    await state.update_data(
        current_question=q_data,
        active_word_id=word.id,
        question_msg_id=message.message_id,
    )

    single_mode = data.get("single_mode", False)
    legend = LEGEND_SINGLE if single_mode else LEGEND_QUIZ

    if q_data["question_type"] == "CHOICE":
        await message.edit_text(
            text=f"{q_data['prompt']}\n\n{HINT_PICK_OPTION}\n\n{legend}",
            reply_markup=get_choice_test_keyboard(q_data["options"], word.id, single_mode),
            parse_mode="HTML",
        )
    else:
        await message.edit_text(
            text=f"{q_data['prompt']}\n\n{HINT_TYPE_ANSWER}\n\n{legend}",
            reply_markup=get_text_answer_keyboard(word.id, single_mode),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("quiz_choice:"), LearningState.answering_test)
async def handle_quiz_choice(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession):
    parts = callback.data.split(":")
    word_id = int(parts[1])
    opt_index = int(parts[2])

    data = await state.get_data()
    q_data = data.get("current_question", {})
    options = q_data.get("options", [])
    user_answer = options[opt_index] if opt_index < len(options) else ""

    await process_quiz_answer(callback.message, state, session, user, user_answer)
    await callback.answer()


@router.callback_query(F.data.startswith("quiz_skip:"), LearningState.answering_test)
async def handle_quiz_skip(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession):
    data = await state.get_data()
    test_queue = data.get("test_queue", [])
    if test_queue:
        await state.update_data(test_queue=test_queue[1:])
    await callback.answer("Пропущено")
    await present_next_quiz_item(callback.message, state, session, user)


@router.message(LearningState.answering_test)
async def handle_quiz_text_answer(message: Message, state: FSMContext, user: User, session: AsyncSession):
    if not message.text:
        await message.answer("Отправьте ответ текстом.")
        return
    user_answer = message.text.strip()

    # Drop "Skip / Finish" from the question we are answering, so stale buttons don't linger
    data = await state.get_data()
    question_msg_id = data.get("question_msg_id")
    if question_msg_id:
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id, message_id=question_msg_id, reply_markup=None
            )
        except Exception:
            pass

    wait_msg = await message.answer("Проверка ответа...")
    await process_quiz_answer(wait_msg, state, session, user, user_answer)


async def process_quiz_answer(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    user_answer: str,
):
    data = await state.get_data()
    q_data = data.get("current_question", {})
    lesson_id = data.get("lesson_id")
    test_queue = data.get("test_queue", [])

    word_id = q_data.get("word_id")
    word_repo = WordRepository(session)
    word = await word_repo.get_by_id(word_id)
    if not word:
        await message.edit_text("Слово не найдено.")
        return

    learning_service = LearningService(session)
    eval_res, xp, achievements = await learning_service.evaluate_and_record_answer(
        user_id=user.id,
        word=word,
        question_type=q_data.get("question_type", "EN_RU"),
        user_answer=user_answer,
        correct_answer=q_data.get("correct_answer", word.translation),
        lesson_id=lesson_id,
        context_sentence=q_data.get("context_sentence"),
    )

    new_queue = test_queue[1:] if test_queue else []
    await state.update_data(test_queue=new_queue)

    status_header = f"<b>✓ Верно</b>  <i>+{xp} XP</i>" if eval_res.is_correct else "<b>✗ Неверно</b>"

    alt_text = ""
    if eval_res.acceptable_alternatives:
        alts = html.escape(", ".join(eval_res.acceptable_alternatives[:3]))
        alt_text = f"\nВарианты: <i>{alts}</i>"

    tip_text = f"\n<i>{html.escape(eval_res.memory_tip)}</i>" if eval_res.memory_tip else ""

    ach_text = ""
    if achievements:
        ach_text = f"\n\n<b>Достижения:</b> " + html.escape(", ".join(achievements))

    feedback_card = (
        f"{status_header}\n\n"
        f"<b><u>{html.escape(word.english_word)}</u></b> — {html.escape(word.translation)}\n\n"
        f"Ваш ответ: <code>{html.escape(user_answer)}</code>\n"
        f"Правильно: <b>{html.escape(eval_res.correct_answer)}</b>{alt_text}\n\n"
        f"<blockquote>{html.escape(eval_res.explanation)}</blockquote>"
        f"{tip_text}{ach_text}"
    )

    single_mode = data.get("single_mode", False)
    has_more = len(new_queue) > 0
    if single_mode:
        feedback_card += "\n\n<i>Нажмите «К карточке», чтобы продолжить изучение.</i>"
    elif not has_more:
        feedback_card += "\n\n<i>Это был последний вопрос. Нажмите «Завершить», чтобы увидеть итог.</i>"

    await message.edit_text(
        text=feedback_card,
        reply_markup=get_test_feedback_keyboard(word.id, next_exists=has_more, single_mode=single_mode),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "quiz_next")
async def handle_quiz_next_button(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession):
    await present_next_quiz_item(callback.message, state, session, user)
    await callback.answer()
