import json
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from learnwords.database.models import UserSettings


class SettingsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_id(self, user_id: int) -> Optional[UserSettings]:
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_settings(self, user_id: int, **kwargs) -> UserSettings:
        settings = await self.get_by_user_id(user_id)
        if not settings:
            settings = UserSettings(user_id=user_id)
            self.session.add(settings)

        for key, value in kwargs.items():
            if key == "preferred_topics" and isinstance(value, list):
                value = json.dumps(value, ensure_ascii=False)
            if hasattr(settings, key):
                setattr(settings, key, value)

        await self.session.commit()
        await self.session.refresh(settings)
        return settings

    def parse_topics(self, settings: UserSettings) -> List[str]:
        try:
            return json.loads(settings.preferred_topics)
        except Exception:
            return ["Everyday Life", "Emotions"]

