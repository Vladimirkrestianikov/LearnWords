from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.keyboards.main_menu import ACHIEVEMENTS_TEXTS
from learnwords.database.models import User
from learnwords.services.achievement_service import AchievementService

router = Router(name="student_achievements")


@router.message(F.text.in_(ACHIEVEMENTS_TEXTS))
async def handle_achievements(message: Message, user: User, session: AsyncSession):
    ach_service = AchievementService(session)
    text = await ach_service.get_achievements_view(user.id)
    await message.answer(text=text, parse_mode="HTML")

