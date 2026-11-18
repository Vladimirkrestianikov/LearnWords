from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from learnwords.services.notification_service import NotificationService
from learnwords.utils.logger import logger

scheduler = AsyncIOScheduler()


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Configures background jobs for spaced repetition reminders."""
    # Check for due reviews every 2 hours
    scheduler.add_job(
        NotificationService.send_due_reviews_reminder,
        trigger="interval",
        hours=2,
        args=[bot],
        id="spaced_repetition_reminders",
        replace_existing=True,
    )
    logger.info("Configured APScheduler tasks.")
    return scheduler

