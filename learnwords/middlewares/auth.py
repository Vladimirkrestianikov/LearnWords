from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.config.settings import settings
from learnwords.database.models import UserStatus, UserRole
from learnwords.database.repositories.user_repo import UserRepository
from learnwords.utils.logger import logger


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Extract telegram user from message or callback
        event_from_user: TgUser = data.get("event_from_user")
        if not event_from_user:
            return await handler(event, data)

        session: AsyncSession = data.get("session")
        if not session:
            return await handler(event, data)

        user_repo = UserRepository(session)
        is_admin_configured = settings.is_admin(event_from_user.id)

        user, created = await user_repo.create_or_get_user(
            telegram_id=event_from_user.id,
            username=event_from_user.username,
            full_name=event_from_user.full_name,
            is_admin=is_admin_configured,
        )

        # Check if user is banned
        if user.status == UserStatus.BANNED:
            if isinstance(event, Message):
                await event.answer("<b>Ваш аккаунт заблокирован администратором.</b>", parse_mode="HTML")
            elif isinstance(event, CallbackQuery):
                await event.answer("Ваш аккаунт заблокирован администратором.", show_alert=True)
            return

        is_admin = (user.role == UserRole.ADMIN) or is_admin_configured
        data["user"] = user
        data["is_admin"] = is_admin

        return await handler(event, data)

