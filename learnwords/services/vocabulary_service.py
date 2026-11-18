import io
import csv
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.database.models import Word, Dictionary, UserSettings
from learnwords.database.repositories.word_repo import WordRepository
from learnwords.database.repositories.dictionary_repo import DictionaryRepository
from learnwords.database.repositories.progress_repo import ProgressRepository
from learnwords.services.openai_service import OpenAIService
from learnwords.utils.logger import logger


class VocabularyService:
    def __init__(self, session: AsyncSession, openai_service: Optional[OpenAIService] = None):
        self.session = session
        self.word_repo = WordRepository(session)
        self.dict_repo = DictionaryRepository(session)
        self.progress_repo = ProgressRepository(session)
        self.openai_service = openai_service or OpenAIService()

    async def get_or_generate_words_for_learning(
        self,
        user_id: int,
        settings: UserSettings,
        count: int = 5,
    ) -> List[Word]:
        """
        1. Read user settings (level, topic).
        2. Get all words user already studied to exclude duplicates.
        3. Try to pull unstudied words from local database first.
        4. If not enough words locally, generate fresh structured batch via OpenAI.
        5. Persist new words in SQLite and return.
        """
        level = settings.english_level
        # Pick current active topic
        topics = settings.preferred_topics
        if isinstance(topics, str):
            import json
            try:
                topic_list = json.loads(topics)
            except Exception:
                topic_list = ["Everyday Life"]
        else:
            topic_list = topics or ["Everyday Life"]

        topic = topic_list[0] if topic_list else "Everyday Life"
        if settings.custom_topic:
            topic = settings.custom_topic

        # Exclude already studied words
        studied_ids = await self.progress_repo.get_studied_word_ids(user_id)

        # Look in DB for unstudied words
        db_words = await self.word_repo.get_words_for_topic_and_level(
            topic=topic,
            level=level,
            exclude_word_ids=studied_ids,
            limit=count,
        )

        words_needed = count - len(db_words)
        if words_needed <= 0:
            return db_words

        # Fetch excluded word strings
        exclude_words_str = [w.english_word for w in db_words]
        if studied_ids:
            for wid in studied_ids[:30]:
                w = await self.word_repo.get_by_id(wid)
                if w:
                    exclude_words_str.append(w.english_word)

        # Generate fresh batch via OpenAI
        logger.info(f"Generating {words_needed} new words via OpenAI for level={level}, topic={topic}")
        generated_cards = await self.openai_service.generate_words(
            level=level,
            topic=topic,
            count=words_needed,
            exclude_words=exclude_words_str,
        )

        created_words = []
        for card in generated_cards:
            synonyms_str = ", ".join(card.synonyms) if card.synonyms else None
            word_obj = await self.word_repo.get_or_create_word(
                english_word=card.english_word,
                translation=card.translation,
                part_of_speech=card.part_of_speech,
                cefr_level=card.cefr_level,
                topic=card.topic or topic,
                example_en=card.example_en,
                example_ru=card.example_ru,
                synonyms=synonyms_str,
                notes=card.notes,
            )
            created_words.append(word_obj)

        return db_words + created_words

    async def export_dictionary_text(self, dictionary_id: int) -> str:
        words = await self.dict_repo.get_words_in_dictionary(dictionary_id, limit=1000)
        lines = []
        for w in words:
            lines.append(f"{w.english_word} — {w.translation}")
        return "\n".join(lines)

    async def export_dictionary_csv(self, dictionary_id: int) -> str:
        words = await self.dict_repo.get_words_in_dictionary(dictionary_id, limit=1000)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["English", "Translation", "CEFR", "Topic", "Part of Speech", "Example EN", "Example RU"])
        for w in words:
            writer.writerow([
                w.english_word,
                w.translation,
                w.cefr_level or "",
                w.topic or "",
                w.part_of_speech or "",
                w.example_en or "",
                w.example_ru or "",
            ])
        return output.getvalue()

