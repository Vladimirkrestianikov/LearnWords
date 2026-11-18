from typing import Optional, List, Tuple
from sqlalchemy import select, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from learnwords.database.models import Dictionary, DictionaryWord, Word


class DictionaryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_dictionaries(
        self, user_id: int, include_public: bool = True
    ) -> List[Dictionary]:
        stmt = select(Dictionary).where(
            or_(
                Dictionary.user_id == user_id,
                and_(Dictionary.is_public == True, Dictionary.user_id != user_id)
                if include_public
                else False,
            )
            if include_public
            else Dictionary.user_id == user_id
        ).order_by(Dictionary.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, dictionary_id: int) -> Optional[Dictionary]:
        stmt = select(Dictionary).where(Dictionary.id == dictionary_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_dictionary(
        self,
        title: str,
        user_id: Optional[int] = None,
        description: Optional[str] = None,
        dictionary_type: str = "USER",
        is_public: bool = False,
    ) -> Dictionary:
        dictionary = Dictionary(
            title=title.strip(),
            user_id=user_id,
            description=description,
            dictionary_type=dictionary_type,
            is_public=is_public,
        )
        self.session.add(dictionary)
        await self.session.commit()
        await self.session.refresh(dictionary)
        return dictionary

    async def delete_dictionary(self, dictionary_id: int) -> bool:
        stmt = delete(Dictionary).where(Dictionary.id == dictionary_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def add_word_to_dictionary(self, dictionary_id: int, word_id: int) -> bool:
        # Check if already in dictionary
        check_stmt = select(DictionaryWord).where(
            and_(
                DictionaryWord.dictionary_id == dictionary_id,
                DictionaryWord.word_id == word_id,
            )
        )
        existing = await self.session.execute(check_stmt)
        if existing.scalar_one_or_none():
            return False

        dw = DictionaryWord(dictionary_id=dictionary_id, word_id=word_id)
        self.session.add(dw)
        await self.session.commit()
        return True

    async def remove_word_from_dictionary(self, dictionary_id: int, word_id: int) -> bool:
        stmt = delete(DictionaryWord).where(
            and_(
                DictionaryWord.dictionary_id == dictionary_id,
                DictionaryWord.word_id == word_id,
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def get_words_in_dictionary(
        self, dictionary_id: int, limit: int = 50, offset: int = 0
    ) -> List[Word]:
        stmt = (
            select(Word)
            .join(DictionaryWord, DictionaryWord.word_id == Word.id)
            .where(DictionaryWord.dictionary_id == dictionary_id)
            .order_by(DictionaryWord.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_words_in_dictionary(self, dictionary_id: int) -> int:
        stmt = select(func.count(DictionaryWord.id)).where(
            DictionaryWord.dictionary_id == dictionary_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_or_create_favorites(self, user_id: int) -> Dictionary:
        stmt = select(Dictionary).where(
            and_(
                Dictionary.user_id == user_id,
                Dictionary.dictionary_type == "FAVORITES",
            )
        )
        result = await self.session.execute(stmt)
        fav_dict = result.scalar_one_or_none()
        if fav_dict and fav_dict.title.startswith("⭐"):
            # Older versions created the dictionary with an emoji in the title
            fav_dict.title = "Избранное"
            await self.session.flush()
        if not fav_dict:
            fav_dict = await self.create_dictionary(
                title="Избранное",
                user_id=user_id,
                description="Слова, добавленные в избранное",
                dictionary_type="FAVORITES",
            )
        return fav_dict
