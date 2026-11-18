import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.database.models import (
    User,
    Word,
    Lesson,
    TestAttempt,
    Import,
    ActivityLog,
    SystemSetting,
    UserStatus,
)


class AdminRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_global_stats(self) -> Dict[str, Any]:
        now = datetime.datetime.now()
        day_ago = now - datetime.timedelta(days=1)
        week_ago = now - datetime.timedelta(days=7)

        # Users
        total_users = (await self.session.execute(select(func.count(User.id)))).scalar() or 0
        new_users_24h = (
            await self.session.execute(
                select(func.count(User.id)).where(User.created_at >= day_ago)
            )
        ).scalar() or 0
        active_users_7d = (
            await self.session.execute(
                select(func.count(User.id)).where(User.last_activity >= week_ago)
            )
        ).scalar() or 0
        banned_users = (
            await self.session.execute(
                select(func.count(User.id)).where(User.status == UserStatus.BANNED)
            )
        ).scalar() or 0

        # Vocabulary
        total_words = (await self.session.execute(select(func.count(Word.id)))).scalar() or 0

        # Lessons & Tests
        total_lessons = (
            await self.session.execute(
                select(func.count(Lesson.id)).where(Lesson.completed == True)
            )
        ).scalar() or 0

        total_tests = (await self.session.execute(select(func.count(TestAttempt.id)))).scalar() or 0
        correct_tests = (
            await self.session.execute(
                select(func.count(TestAttempt.id)).where(TestAttempt.is_correct == True)
            )
        ).scalar() or 0
        accuracy = round((correct_tests / total_tests * 100), 1) if total_tests > 0 else 0.0

        # Imports
        total_imports = (await self.session.execute(select(func.count(Import.id)))).scalar() or 0

        # API token / calls estimate from ActivityLog
        ai_calls = (
            await self.session.execute(
                select(func.count(ActivityLog.id)).where(ActivityLog.action.like("AI_%"))
            )
        ).scalar() or 0

        return {
            "total_users": total_users,
            "new_users_24h": new_users_24h,
            "active_users_7d": active_users_7d,
            "banned_users": banned_users,
            "total_words": total_words,
            "total_lessons": total_lessons,
            "total_tests": total_tests,
            "overall_accuracy": accuracy,
            "total_imports": total_imports,
            "ai_calls": ai_calls,
        }

    async def get_system_setting(self, key: str, default: str = "") -> str:
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        setting = (await self.session.execute(stmt)).scalar_one_or_none()
        return setting.value if setting else default

    async def set_system_setting(
        self, key: str, value: str, description: Optional[str] = None
    ) -> SystemSetting:
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        setting = (await self.session.execute(stmt)).scalar_one_or_none()
        if not setting:
            setting = SystemSetting(
                key=key,
                value=value,
                description=description,
                updated_at=datetime.datetime.now(),
            )
            self.session.add(setting)
        else:
            setting.value = value
            if description:
                setting.description = description
            setting.updated_at = datetime.datetime.now()

        await self.session.commit()
        await self.session.refresh(setting)
        return setting

    async def log_activity(
        self, user_id: Optional[int], action: str, details: Optional[str] = None
    ) -> None:
        log = ActivityLog(
            user_id=user_id,
            action=action,
            details=details,
            created_at=datetime.datetime.now(),
        )
        self.session.add(log)
        await self.session.commit()

    async def get_recent_logs(self, limit: int = 20) -> List[ActivityLog]:
        stmt = select(ActivityLog).order_by(desc(ActivityLog.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

