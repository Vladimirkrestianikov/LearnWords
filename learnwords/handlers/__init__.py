from aiogram import Router

from learnwords.handlers.common import start
from learnwords.handlers.student import settings, progress, achievements
from learnwords.handlers.learning import learning, practice, review
from learnwords.handlers.dictionaries import dictionaries
from learnwords.handlers.imports import imports
from learnwords.handlers.admin import panel, users, stats, ai_settings, broadcast, dictionaries as admin_dicts


def setup_routers() -> Router:
    main_router = Router(name="main_router")

    # Common & Navigation
    main_router.include_router(start.router)

    # Student personal area & Settings
    main_router.include_router(settings.router)
    main_router.include_router(progress.router)
    main_router.include_router(achievements.router)

    # Learning & SM-2
    main_router.include_router(learning.router)
    main_router.include_router(practice.router)
    main_router.include_router(review.router)

    # Dictionaries & Vocabulary Imports
    main_router.include_router(dictionaries.router)
    main_router.include_router(imports.router)

    # Admin Control Panel
    main_router.include_router(panel.router)
    main_router.include_router(users.router)
    main_router.include_router(stats.router)
    main_router.include_router(ai_settings.router)
    main_router.include_router(broadcast.router)
    main_router.include_router(admin_dicts.router)

    return main_router

