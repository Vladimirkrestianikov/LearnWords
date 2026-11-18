import json
import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from learnwords.database.models import Import, ImportWord, Word, DictionaryWord, Dictionary
from learnwords.database.repositories.word_repo import WordRepository
from learnwords.database.repositories.dictionary_repo import DictionaryRepository


class ImportRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.word_repo = WordRepository(session)
        self.dict_repo = DictionaryRepository(session)

    async def create_import(
        self,
        user_id: int,
        filename: str,
        target_dictionary_id: Optional[int] = None,
    ) -> Import:
        imp = Import(
            user_id=user_id,
            filename=filename,
            target_dictionary_id=target_dictionary_id,
            status="PENDING_VERIFICATION",
            total_words=0,
            processed_words=0,
            duplicate_words=0,
            needs_clarification_words=0,
            created_at=datetime.datetime.now(),
        )
        self.session.add(imp)
        await self.session.commit()
        await self.session.refresh(imp)
        return imp

    async def get_by_id(self, import_id: int) -> Optional[Import]:
        stmt = (
            select(Import)
            .options(selectinload(Import.words))
            .where(Import.id == import_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pending_import(self, user_id: int) -> Optional[Import]:
        stmt = (
            select(Import)
            .options(selectinload(Import.words))
            .where(
                and_(
                    Import.user_id == user_id,
                    Import.status == "PENDING_VERIFICATION",
                )
            )
            .order_by(Import.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_staged_words(
        self, import_id: int, parsed_words: List[Dict[str, Any]]
    ) -> Import:
        imp = await self.get_by_id(import_id)
        if not imp:
            raise ValueError(f"Import {import_id} not found")

        total = len(parsed_words)
        duplicates = 0
        clarifications = 0
        valid = 0

        # Preload existing words to detect duplicates
        existing_words = set()
        for w in parsed_words:
            eng = w.get("english_word", "").strip().lower()
            if not eng:
                continue
            existing = await self.word_repo.find_by_english(eng)
            if existing:
                existing_words.add(eng)

        for item in parsed_words:
            eng = item.get("english_word", "").strip()
            ru = item.get("translation", "").strip()
            if not eng:
                continue

            status = "VALID"
            if eng.lower() in existing_words:
                status = "DUPLICATE"
                duplicates += 1
            elif not ru or len(ru) < 2 or "?" in ru:
                status = "NEEDS_CLARIFICATION"
                clarifications += 1
            else:
                valid += 1

            synonyms = item.get("synonyms")
            if isinstance(synonyms, list):
                synonyms = ", ".join(synonyms)

            iw = ImportWord(
                import_id=import_id,
                english_word=eng,
                translation=ru,
                part_of_speech=item.get("part_of_speech"),
                cefr_level=item.get("cefr_level"),
                topic=item.get("topic"),
                example_en=item.get("example_en"),
                example_ru=item.get("example_ru"),
                synonyms=synonyms,
                notes=item.get("notes"),
                ai_data=json.dumps(item.get("ai_data", {}), ensure_ascii=False) if item.get("ai_data") else None,
                status=status,
            )
            self.session.add(iw)

        imp.total_words = total
        imp.processed_words = len(parsed_words)
        imp.duplicate_words = duplicates
        imp.needs_clarification_words = clarifications

        await self.session.commit()
        await self.session.refresh(imp, attribute_names=["words"])
        return imp

    async def get_words(
        self, import_id: int, status_filter: Optional[str] = None
    ) -> List[ImportWord]:
        stmt = select(ImportWord).where(ImportWord.import_id == import_id)
        if status_filter:
            stmt = stmt.where(ImportWord.status == status_filter)
        stmt = stmt.order_by(ImportWord.id.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_word(self, word_id: int, **kwargs) -> Optional[ImportWord]:
        stmt = select(ImportWord).where(ImportWord.id == word_id)
        result = await self.session.execute(stmt)
        word = result.scalar_one_or_none()
        if word:
            for k, v in kwargs.items():
                if hasattr(word, k):
                    setattr(word, k, v)
            await self.session.commit()
            await self.session.refresh(word)
        return word

    async def delete_word(self, word_id: int) -> bool:
        stmt = delete(ImportWord).where(ImportWord.id == word_id)
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.rowcount > 0

    async def confirm_import(
        self,
        import_id: int,
        target_dict_id: Optional[int] = None,
        custom_dict_title: Optional[str] = None,
    ) -> Tuple[int, Dictionary]:
        """
        Transfers validated import words into words table and assigns them to target dictionary.
        Marks import session as CONFIRMED.
        """
        imp = await self.get_by_id(import_id)
        if not imp:
            raise ValueError(f"Import {import_id} not found")

        # Get or create target dictionary
        if target_dict_id:
            target_dict = await self.dict_repo.get_by_id(target_dict_id)
        else:
            title = custom_dict_title or f"Импорт {datetime.date.today().strftime('%d.%m.%Y')}"
            target_dict = await self.dict_repo.create_dictionary(
                title=title,
                user_id=imp.user_id,
                description=f"Импортировано из {imp.filename}",
                dictionary_type="USER",
            )

        # Get all words from staging except deleted
        stmt = select(ImportWord).where(
            and_(
                ImportWord.import_id == import_id,
                ImportWord.status != "DELETED",
            )
        )
        result = await self.session.execute(stmt)
        words_to_add = result.scalars().all()

        added_count = 0
        for iw in words_to_add:
            # Create or get word in main dictionary
            word = await self.word_repo.get_or_create_word(
                english_word=iw.english_word,
                translation=iw.translation,
                part_of_speech=iw.part_of_speech,
                cefr_level=iw.cefr_level,
                topic=iw.topic,
                example_en=iw.example_en,
                example_ru=iw.example_ru,
                synonyms=iw.synonyms,
                notes=iw.notes,
            )
            # Add to dictionary
            added = await self.dict_repo.add_word_to_dictionary(target_dict.id, word.id)
            if added:
                added_count += 1

        imp.status = "CONFIRMED"
        imp.target_dictionary_id = target_dict.id
        await self.session.commit()

        return added_count, target_dict

    async def cancel_import(self, import_id: int) -> bool:
        imp = await self.get_by_id(import_id)
        if imp:
            imp.status = "CANCELLED"
            await self.session.commit()
            return True
        return False

