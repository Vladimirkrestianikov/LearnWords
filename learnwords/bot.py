import asyncio
import sys
from pathlib import Path

# Add project root to sys.path for direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from learnwords.config.settings import settings
from learnwords.database.database import init_db, close_db, async_session_maker
from learnwords.database.repositories.achievement_repo import AchievementRepository
from learnwords.middlewares.database import DatabaseMiddleware
from learnwords.middlewares.auth import AuthMiddleware
from learnwords.middlewares.throttling import ThrottlingMiddleware
from learnwords.handlers import setup_routers
from learnwords.scheduler.tasks import setup_scheduler
from learnwords.utils.logger import logger


async def main():
    logger.info("Starting LearnWords Telegram Bot initialization...")

    if not settings.BOT_TOKEN or settings.BOT_TOKEN == "mock-token":
        logger.warning(
            "BOT_TOKEN is not configured in .env! "
            "Please provide a valid token from @BotFather to run polling."
        )

    # 1. Initialize Database schema
    await init_db()

    # 2. Seed initial system data (achievements)
    async with async_session_maker() as session:
        ach_repo = AchievementRepository(session)
        await ach_repo.seed_default_achievements()

    # 3. Create Bot and Dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN if settings.BOT_TOKEN else "123456:dummytokenforinitialization",
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # 4. Setup Middlewares
    dp.update.middleware(DatabaseMiddleware())
    dp.update.middleware(AuthMiddleware())
    dp.message.middleware(ThrottlingMiddleware())

    # 5. Register Routers
    main_router = setup_routers()
    dp.include_router(main_router)

    # 6. Setup APScheduler
    scheduler = setup_scheduler(bot)
    scheduler.start()

    logger.info("LearnWords is fully initialized and ready.")

    try:
        # If token is not set, don't attempt live polling to avoid immediate crash
        if not settings.BOT_TOKEN or "dummy" in settings.BOT_TOKEN:
            logger.info("Bot initialized in offline/test mode (no BOT_TOKEN set). Exiting gracefully.")
            return
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Error during bot execution: {e}")
    finally:
        scheduler.shutdown(wait=False)
        await close_db()
        await bot.session.close()
        logger.info("Bot execution terminated cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user.")
