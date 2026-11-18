from typing import Optional, List
from sqlalchemy import select, or_, func, not_
from sqlalchemy.ext.asyncio import AsyncSession
from learnwords.database.models import Word, WordProgress


class WordRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, word_id: int) -> Optional[Word]:
        stmt = select(Word).where(Word.id == word_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_english(self, english_word: str) -> Optional[Word]:
        stmt = select(Word).where(func.lower(Word.english_word) == english_word.strip().lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_word(
        self,
        english_word: str,
        translation: str,
        part_of_speech: Optional[str] = None,
        cefr_level: Optional[str] = None,
        topic: Optional[str] = None,
        example_en: Optional[str] = None,
        example_ru: Optional[str] = None,
        synonyms: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Word:
        word = await self.find_by_english(english_word)
        if word:
            # Update fields if richer data is provided
            if translation and not word.translation:
                word.translation = translation
            if example_en and not word.example_en:
                word.example_en = example_en
            if example_ru and not word.example_ru:
                word.example_ru = example_ru
            if cefr_level and not word.cefr_level:
                word.cefr_level = cefr_level
            if topic and not word.topic:
                word.topic = topic
            await self.session.commit()
            return word

        word = Word(
            english_word=english_word.strip(),
            translation=translation.strip(),
            part_of_speech=part_of_speech,
            cefr_level=cefr_level,
            topic=topic,
            example_en=example_en,
            example_ru=example_ru,
            synonyms=synonyms,
            notes=notes,
        )
        self.session.add(word)
        await self.session.commit()
        await self.session.refresh(word)
        return word

    async def search_words(self, query: str, limit: int = 20) -> List[Word]:
        q = f"%{query.strip().lower()}%"
        stmt = (
            select(Word)
            .where(
                or_(
                    func.lower(Word.english_word).ilike(q),
                    func.lower(Word.translation).ilike(q),
                )
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_words_for_topic_and_level(
        self,
        topic: Optional[str],
        level: Optional[str],
        exclude_word_ids: List[int],
        limit: int = 10,
    ) -> List[Word]:
        stmt = select(Word)
        if topic and topic != "Custom Topic":
            stmt = stmt.where(Word.topic.ilike(f"%{topic}%"))
        if level:
            stmt = stmt.where(Word.cefr_level == level)
        if exclude_word_ids:
            stmt = stmt.where(not_(Word.id.in_(exclude_word_ids)))
        stmt = stmt.order_by(func.random()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_words(self) -> int:
        stmt = select(func.count(Word.id))
        result = await self.session.execute(stmt)
        return result.scalar() or 0

