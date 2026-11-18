import datetime
from aiogram import Bot
from sqlalchemy import select, and_
from learnwords.database.database import async_session_maker
from learnwords.database.models import User, UserSettings, WordProgress
from learnwords.utils.logger import logger


class NotificationService:
    @staticmethod
    async def send_due_reviews_reminder(bot: Bot) -> None:
        """Scheduled check for users who have words pending review."""
        try:
            async with async_session_maker() as session:
                now = datetime.datetime.now()
                # Find users with due words and reminder enabled
                stmt = (
                    select(User.telegram_id, User.id)
                    .join(UserSettings, UserSettings.user_id == User.id)
                    .join(WordProgress, WordProgress.user_id == User.id)
                    .where(
                        and_(
                            UserSettings.reminder_enabled == True,
                            WordProgress.next_review_at <= now,
                        )
                    )
                    .distinct()
                )
                result = await session.execute(stmt)
                users = result.all()

                for tg_id, uid in users:
                    try:
                        await bot.send_message(
                            chat_id=tg_id,
                            text=(
                                "<b>Пора повторить слова</b>\n\n"
                                "Несколько слов ждут повторения — это займёт пару минут.\n\n"
                                "Нажмите <b>Повторение</b> в главном меню."
                            ),
                            parse_mode="HTML",
                        )
                    except Exception as send_err:
                        logger.debug(f"Could not send reminder to {tg_id}: {send_err}")
        except Exception as e:
            logger.error(f"Error in send_due_reviews_reminder: {e}")

