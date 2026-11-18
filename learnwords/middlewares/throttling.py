import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from learnwords.config.settings import settings


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = None):
        self.rate_limit = rate_limit or settings.RATE_LIMIT_SECONDS
        self.last_user_time: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        event_from_user = data.get("event_from_user")
        if event_from_user:
            user_id = event_from_user.id
            now = time.time()
            last_time = self.last_user_time.get(user_id, 0.0)

            if now - last_time < self.rate_limit:
                if isinstance(event, Message):
                    # Silently ignore flood message
                    return
            self.last_user_time[user_id] = now

        return await handler(event, data)

