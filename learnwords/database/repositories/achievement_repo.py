import datetime
from typing import List, Tuple, Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from learnwords.database.models import Achievement, UserAchievement, User, WordProgress, Lesson, Dictionary, Import
from learnwords.utils.logger import logger


DEFAULT_ACHIEVEMENTS = [
    {
        "code": "FIRST_WORD",
        "title": "Первый шаг",
        "description": "Изучено первое слово в LearnWords",
        "icon": "🌱",
        "xp_reward": 25,
    },
    {
        "code": "FIRST_50_WORDS",
        "title": "Первые 50 слов",
        "description": "Успешно изучено 50 английских слов",
        "icon": "🏅",
        "xp_reward": 100,
    },
    {
        "code": "VOCABULARY_MASTER",
        "title": "Мастер словарного запаса",
        "description": "Изучено более 500 слов",
        "icon": "🧠",
        "xp_reward": 500,
    },
    {
        "code": "STREAK_7_DAYS",
        "title": "Недельный огонь",
        "description": "7 дней обучения подряд без пропусков",
        "icon": "🔥",
        "xp_reward": 150,
    },
    {
        "code": "PERFECT_LESSON",
        "title": "Идеальный урок",
        "description": "Завершено интерактивное занятие без единой ошибки",
        "icon": "🎯",
        "xp_reward": 75,
    },
    {
        "code": "DICTIONARY_BUILDER",
        "title": "Свой словарь",
        "description": "Создан первый персональный словарь",
        "icon": "📚",
        "xp_reward": 50,
    },
    {
        "code": "IMPORT_EXPLORER",
        "title": "Мастер импорта",
        "description": "Импортирован и сохранён собственный список слов",
        "icon": "📥",
        "xp_reward": 75,
    },
    {
        "code": "REVIEW_CHAMPION",
        "title": "Чемпион повторения",
        "description": "Пройдено интервальное повторение 10 раз",
        "icon": "🔄",
        "xp_reward": 100,
    },
]


class AchievementRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def seed_default_achievements(self) -> None:
        """Seed initial achievements into DB if not present."""
        for ach_data in DEFAULT_ACHIEVEMENTS:
            stmt = select(Achievement).where(Achievement.code == ach_data["code"])
            existing = (await self.session.execute(stmt)).scalar_one_or_none()
            if not existing:
                achievement = Achievement(
                    code=ach_data["code"],
                    title=ach_data["title"],
                    description=ach_data["description"],
                    icon=ach_data["icon"],
                    xp_reward=ach_data["xp_reward"],
                )
                self.session.add(achievement)
        await self.session.commit()

    async def get_all_achievements(self) -> List[Achievement]:
        stmt = select(Achievement).order_by(Achievement.id.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_achievements(
        self, user_id: int
    ) -> List[Tuple[Achievement, Optional[UserAchievement]]]:
        achievements = await self.get_all_achievements()
        stmt = select(UserAchievement).where(UserAchievement.user_id == user_id)
        result = await self.session.execute(stmt)
        user_ach_map = {ua.achievement_id: ua for ua in result.scalars().all()}

        return [(ach, user_ach_map.get(ach.id)) for ach in achievements]

    async def award_achievement(self, user_id: int, code: str) -> Optional[Achievement]:
        """Awards an achievement if not already earned, returns achievement if newly awarded."""
        stmt = select(Achievement).where(Achievement.code == code)
        ach = (await self.session.execute(stmt)).scalar_one_or_none()
        if not ach:
            return None

        # Check if already unlocked
        ua_stmt = select(UserAchievement).where(
            and_(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == ach.id,
            )
        )
        existing = (await self.session.execute(ua_stmt)).scalar_one_or_none()
        if existing:
            return None

        ua = UserAchievement(
            user_id=user_id,
            achievement_id=ach.id,
            unlocked_at=datetime.datetime.now(),
        )
        self.session.add(ua)

        # Award XP
        user_stmt = select(User).where(User.id == user_id)
        user = (await self.session.execute(user_stmt)).scalar_one_or_none()
        if user:
            user.xp += ach.xp_reward
            user.level = max(1, 1 + int((user.xp / 100) ** 0.5))

        await self.session.commit()
        logger.info(f"User {user_id} earned achievement: {ach.title} (+{ach.xp_reward} XP)")
        return ach

