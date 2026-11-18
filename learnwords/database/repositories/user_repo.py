import datetime
from typing import Optional, List, Tuple
from sqlalchemy import select, update, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from learnwords.database.models import User, UserSettings, UserRole, UserStatus
from learnwords.utils.logger import logger


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        stmt = (
            select(User)
            .options(selectinload(User.settings))
            .where(User.telegram_id == telegram_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        stmt = (
            select(User)
            .options(selectinload(User.settings))
            .where(User.id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_or_get_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
        is_admin: bool = False
    ) -> Tuple[User, bool]:
        """Returns tuple of (user, created_flag)."""
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            # Update user info if changed
            changed = False
            if user.username != username:
                user.username = username
                changed = True
            if user.full_name != full_name:
                user.full_name = full_name
                changed = True
            user.last_activity = datetime.datetime.now()
            if changed:
                await self.session.commit()
            return user, False

        # Create new user
        role = UserRole.ADMIN if is_admin else UserRole.STUDENT
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            role=role,
            status=UserStatus.ACTIVE,
            xp=0,
            level=1,
            streak_days=1,
            last_streak_date=datetime.date.today(),
            created_at=datetime.datetime.now(),
            last_activity=datetime.datetime.now(),
        )
        self.session.add(user)
        await self.session.flush()

        # Create default user settings
        settings = UserSettings(
            user_id=user.id,
            english_level="B1",
            preferred_topics='["Everyday Life", "Emotions"]',
            daily_word_goal=10,
            difficulty="STANDARD",
            explanation_language="RU",
            learning_mode="NEW_WORDS",
            reminder_enabled=True,
            reminder_time="10:00"
        )
        self.session.add(settings)
        await self.session.commit()
        await self.session.refresh(user, attribute_names=["settings"])

        logger.info(f"Registered new user: tg_id={telegram_id}, role={role}")
        return user, True

    async def update_activity(self, user_id: int) -> None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(last_activity=datetime.datetime.now())
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_status(self, user_id: int, status: str) -> None:
        stmt = update(User).where(User.id == user_id).values(status=status)
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_role(self, user_id: int, role: str) -> None:
        stmt = update(User).where(User.id == user_id).values(role=role)
        await self.session.execute(stmt)
        await self.session.commit()

    async def add_xp(self, user_id: int, amount: int) -> Tuple[int, int, bool]:
        """Adds XP to user and calculates if level-up occurred.
        Level formula: Level N requires N * 100 XP.
        """
        user = await self.get_by_id(user_id)
        if not user:
            return 0, 1, False

        user.xp += amount
        # Level calculation: level 1 is 0-99, level 2 is 100-299, etc.
        # Simple formula: level = 1 + int((xp / 100) ** 0.5)
        new_level = max(1, 1 + int((user.xp / 100) ** 0.5))
        leveled_up = new_level > user.level
        if leveled_up:
            user.level = new_level

        await self.session.commit()
        return user.xp, user.level, leveled_up

    async def update_streak(self, user_id: int) -> int:
        """Update daily streak for user."""
        user = await self.get_by_id(user_id)
        if not user:
            return 0

        today = datetime.date.today()
        if user.last_streak_date:
            last_date = user.last_streak_date
            if isinstance(last_date, datetime.datetime):
                last_date = last_date.date()

            diff = (today - last_date).days
            if diff == 0:
                # Already active today
                return user.streak_days
            elif diff == 1:
                # Consecutive day streak
                user.streak_days += 1
                user.last_streak_date = today
            else:
                # Streak broken
                user.streak_days = 1
                user.last_streak_date = today
        else:
            user.streak_days = 1
            user.last_streak_date = today

        await self.session.commit()
        return user.streak_days

    async def list_users(
        self,
        limit: int = 20,
        offset: int = 0,
        search: Optional[str] = None
    ) -> List[User]:
        stmt = select(User).options(selectinload(User.settings))
        if search:
            if search.isdigit():
                stmt = stmt.where(User.telegram_id == int(search))
            else:
                stmt = stmt.where(
                    or_(
                        User.username.ilike(f"%{search}%"),
                        User.full_name.ilike(f"%{search}%")
                    )
                )
        stmt = stmt.order_by(User.last_activity.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_users(self) -> int:
        stmt = select(func.count(User.id))
        result = await self.session.execute(stmt)
        return result.scalar() or 0

