from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from learnwords.database.repositories.achievement_repo import AchievementRepository


class AchievementService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.achievement_repo = AchievementRepository(session)

    async def get_achievements_view(self, user_id: int) -> str:
        pairs = await self.achievement_repo.get_user_achievements(user_id)

        unlocked_count = sum(1 for _, ua in pairs if ua is not None)
        total_count = len(pairs)

        lines = [
            f"<b>Достижения ({unlocked_count}/{total_count})</b>\n"
        ]

        for ach, ua in pairs:
            if ua:
                date_str = ua.unlocked_at.strftime("%d.%m.%Y")
                lines.append(
                    f"✓ <b>{ach.title}</b> (+{ach.xp_reward} XP)\n"
                    f"<i>{ach.description}</i> · получено {date_str}"
                )
            else:
                lines.append(
                    f"○ <b>{ach.title}</b> (+{ach.xp_reward} XP)\n"
                    f"<i>{ach.description}</i>"
                )

        return "\n\n".join(lines)
