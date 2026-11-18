from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.database.models import User
from learnwords.database.repositories.user_repo import UserRepository
from learnwords.database.repositories.lesson_repo import LessonRepository
from learnwords.database.repositories.progress_repo import ProgressRepository


class StatisticsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.lesson_repo = LessonRepository(session)
        self.progress_repo = ProgressRepository(session)

    async def get_student_dashboard(self, user_id: int, days: Optional[int] = None) -> Dict[str, Any]:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        review_counts = await self.progress_repo.get_review_counts(user_id)
        performance = await self.lesson_repo.get_user_performance(user_id, days=days)
        topic_stats = await self.lesson_repo.get_topic_stats(user_id)
        weak_words = await self.lesson_repo.get_weak_words(user_id, limit=5)

        return {
            "user": user,
            "review_counts": review_counts,
            "performance": performance,
            "topic_stats": topic_stats,
            "weak_words": weak_words,
            "streak_days": user.streak_days,
            "xp": user.xp,
            "level": user.level,
        }

    async def format_progress_message(self, user_id: int, timeframe_days: Optional[int] = None) -> str:
        data = await self.get_student_dashboard(user_id, days=timeframe_days)
        user: User = data["user"]
        rc = data["review_counts"]
        perf = data["performance"]
        topics = data["topic_stats"]
        weak = data["weak_words"]

        period_label = "Все время"
        if timeframe_days == 1:
            period_label = "Сегодня"
        elif timeframe_days == 7:
            period_label = "7 дней"
        elif timeframe_days == 30:
            period_label = "30 дней"

        weak_lines = []
        for word, errors, total in weak[:4]:
            weak_lines.append(f"• <b>{word.english_word}</b> ({word.translation}) — {errors} ош. из {total}")
        weak_text = "\n".join(weak_lines) if weak_lines else "<i>Нет сложных слов. Отличный результат.</i>"

        topic_lines = []
        for t in topics[:5]:
            topic_lines.append(f"• {t['topic']} — <b>{t['accuracy']}%</b> ({t['correct']}/{t['total']})")
        topics_text = "\n".join(topic_lines) if topic_lines else "<i>Недостаточно данных по темам</i>"

        msg = (
            f"<b>Прогресс ({period_label})</b>\n\n"
            f"Ученик: <b>{user.full_name or user.username or 'Student'}</b>\n"
            f"Уровень: <b>{user.level}</b> · Опыт: <b>{user.xp} XP</b> · Серия: <b>{user.streak_days} дн.</b>\n\n"
            f"<b>Слова:</b>\n"
            f"Изучено: <b>{rc['total_learned']}</b> · Запомнено: <b>{rc['mastered']}</b>\n"
            f"К повторению: <b>{rc['due']}</b> · Сложные: <b>{rc['difficult']}</b>\n\n"
            f"<b>Успеваемость:</b>\n"
            f"Уроков: <b>{perf['completed_lessons']}</b> · Точность: <b>{perf['accuracy']}%</b>\n"
            f"Верно: {perf['correct']} · Ошибок: {perf['incorrect']}\n\n"
            f"<b>По темам:</b>\n{topics_text}\n\n"
            f"<b>Слова, требующие внимания:</b>\n{weak_text}"
        )
        return msg
