import pytest
from learnwords.services.learning_service import LearningService
from learnwords.database.repositories.user_repo import UserRepository
from learnwords.database.repositories.word_repo import WordRepository
from learnwords.database.repositories.achievement_repo import AchievementRepository
from learnwords.database.models import WordProgressStatus


@pytest.mark.asyncio
async def test_learning_session_flow(test_session):
    # 1. Setup user & achievements
    user_repo = UserRepository(test_session)
    user, _ = await user_repo.create_or_get_user(telegram_id=987654)

    ach_repo = AchievementRepository(test_session)
    await ach_repo.seed_default_achievements()

    # 2. Start learning
    learning_service = LearningService(test_session)
    lesson, words = await learning_service.start_lesson(user.id)

    assert lesson.id is not None
    assert len(words) > 0
    test_word = words[0]

    # 3. Card formatting
    card_html = await learning_service.format_word_card(test_word, 1, len(words), is_favorite=False)
    assert test_word.english_word in card_html
    assert test_word.translation in card_html

    # 4. Generate all 7 question types
    for q_type in learning_service.QUESTION_TYPES:
        q_data = await learning_service.generate_test_question(test_word, question_type=q_type, other_words=words)
        assert q_data["question_type"] == q_type
        assert "prompt" in q_data
        assert "correct_answer" in q_data

    # 5. Evaluate and record answer
    initial_xp = user.xp
    eval_res, xp, achievements = await learning_service.evaluate_and_record_answer(
        user_id=user.id,
        word=test_word,
        question_type="EN_RU",
        user_answer=test_word.translation,
        correct_answer=test_word.translation,
        lesson_id=lesson.id,
    )

    assert eval_res.is_correct is True
    assert xp > 0
    assert len(achievements) >= 1  # FIRST_WORD unlocked!

    # Check user XP updated in DB (earned 15 XP from answer + 25 XP from FIRST_WORD achievement)
    refreshed_user = await user_repo.get_by_id(user.id)
    assert refreshed_user.xp == initial_xp + xp + 25

    # Check progress SM-2 updated
    prog = await learning_service.progress_repo.get_progress(user.id, test_word.id)
    assert prog is not None
    assert prog.correct_answers == 1
    assert prog.repetitions == 1
    assert prog.status == WordProgressStatus.LEARNING
