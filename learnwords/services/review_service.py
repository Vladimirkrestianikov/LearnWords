from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.database.models import Word, WordProgress
from learnwords.database.repositories.progress_repo import ProgressRepository
from learnwords.database.repositories.word_repo import WordRepository
from learnwords.database.repositories.achievement_repo import AchievementRepository
from learnwords.services.openai_service import OpenAIService


class ReviewService:
    def __init__(self, session: AsyncSession, openai_service: Optional[OpenAIService] = None):
        self.session = session
        self.progress_repo = ProgressRepository(session)
        self.word_repo = WordRepository(session)
        self.achievement_repo = AchievementRepository(session)
        self.openai_service = openai_service or OpenAIService()

    async def get_review_dashboard(self, user_id: int) -> Dict[str, Any]:
        """Fetch spaced repetition review counters."""
        counts = await self.progress_repo.get_review_counts(user_id)
        return counts

    async def get_words_for_review_session(
        self, user_id: int, only_difficult: bool = False, limit: int = 10
    ) -> List[Word]:
        if only_difficult:
            pairs = await self.progress_repo.get_difficult_words(user_id, limit=limit)
        else:
            pairs = await self.progress_repo.get_words_for_review(user_id, limit=limit)

        return [word for _, word in pairs]

