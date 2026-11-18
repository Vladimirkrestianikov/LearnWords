import pytest
from learnwords.database.repositories.user_repo import UserRepository
from learnwords.database.repositories.word_repo import WordRepository
from learnwords.database.repositories.lesson_repo import LessonRepository
from learnwords.services.statistics_service import StatisticsService


@pytest.mark.asyncio
async def test_statistics_aggregation(test_session):
    user_repo = UserRepository(test_session)
    user, _ = await user_repo.create_or_get_user(telegram_id=33333)

    word_repo = WordRepository(test_session)
    w1 = await word_repo.get_or_create_word("Happy", "Счастливый", topic="Emotions")
    w2 = await word_repo.get_or_create_word("Engine", "Двигатель", topic="Cars")

    lesson_repo = LessonRepository(test_session)
    lesson = await lesson_repo.create_lesson(user.id, topic="Emotions", level="B1", word_ids=[w1.id, w2.id])

    # Record 2 correct attempts for w1 and 1 incorrect for w2
    await lesson_repo.record_attempt(user.id, w1.id, "EN_RU", "Счастливый", "Счастливый", True, lesson.id)
    await lesson_repo.record_attempt(user.id, w1.id, "RU_EN", "Happy", "Happy", True, lesson.id)
    await lesson_repo.record_attempt(user.id, w2.id, "EN_RU", "Колесо", "Двигатель", False, lesson.id)

    await lesson_repo.complete_lesson(lesson.id)

    stats_service = StatisticsService(test_session)
    dash = await stats_service.get_student_dashboard(user.id)

    perf = dash["performance"]
    assert perf["total_attempts"] == 3
    assert perf["correct"] == 2
    assert perf["incorrect"] == 1
    assert perf["accuracy"] == 66.7
    assert perf["completed_lessons"] == 1

    weak = dash["weak_words"]
    assert len(weak) == 1
    assert weak[0][0].english_word == "Engine"
    assert weak[0][1] == 1  # 1 error

    msg = await stats_service.format_progress_message(user.id)
    assert "66.7%" in msg
    assert "Engine" in msg

