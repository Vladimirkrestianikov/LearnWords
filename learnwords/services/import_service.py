from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.database.models import Import, ImportWord, Dictionary
from learnwords.database.repositories.import_repo import ImportRepository
from learnwords.database.repositories.dictionary_repo import DictionaryRepository
from learnwords.database.repositories.achievement_repo import AchievementRepository
from learnwords.services.openai_service import OpenAIService
from learnwords.utils.file_parser import FileParser
from learnwords.utils.validators import validate_file_upload
from learnwords.utils.logger import logger


class ImportService:
    def __init__(self, session: AsyncSession, openai_service: Optional[OpenAIService] = None):
        self.session = session
        self.import_repo = ImportRepository(session)
        self.dict_repo = DictionaryRepository(session)
        self.achievement_repo = AchievementRepository(session)
        self.openai_service = openai_service or OpenAIService()

    async def stage_import_from_text(
        self,
        user_id: int,
        raw_text: str,
        filename: str = "Pasted_Text.txt",
        default_topic: Optional[str] = None,
    ) -> Import:
        """Process raw text through AI and store in staging under 'PENDING_VERIFICATION'."""
        imp = await self.import_repo.create_import(
            user_id=user_id,
            filename=filename,
        )

        analysis = await self.openai_service.analyze_raw_vocabulary(
            raw_text=raw_text,
            default_topic=default_topic,
        )

        words_data = [w.model_dump() for w in analysis.words]
        imp = await self.import_repo.add_staged_words(imp.id, words_data)
        return imp

    async def stage_import_from_file(
        self,
        user_id: int,
        file_bytes: bytes,
        filename: str,
        default_topic: Optional[str] = None,
    ) -> Tuple[Optional[Import], Optional[str]]:
        """Validate, extract text from file, analyze with AI, and stage."""
        valid, msg = validate_file_upload(filename, len(file_bytes))
        if not valid:
            return None, msg

        extracted_text = FileParser.extract_text(file_bytes, filename)
        if not extracted_text.strip():
            return None, "Не удалось извлечь текст из файла. Проверьте содержимое документа."

        imp = await self.stage_import_from_text(
            user_id=user_id,
            raw_text=extracted_text,
            filename=filename,
            default_topic=default_topic,
        )
        return imp, None

    async def get_import_preview_summary(self, import_id: int) -> str:
        imp = await self.import_repo.get_by_id(import_id)
        if not imp:
            return "Сессия импорта не найдена."

        words = await self.import_repo.get_words(import_id)
        valid_words = [w for w in words if w.status == "VALID"]
        duplicate_words = [w for w in words if w.status == "DUPLICATE"]
        clarification_words = [w for w in words if w.status == "NEEDS_CLARIFICATION"]

        preview_lines = []
        for i, w in enumerate(valid_words[:7], start=1):
            cefr = f" [{w.cefr_level}]" if w.cefr_level else ""
            preview_lines.append(f"{i}. <b>{w.english_word}</b> — {w.translation}{cefr}")

        if len(valid_words) > 7:
            preview_lines.append(f"... и ещё {len(valid_words) - 7} слов")

        preview_text = "\n".join(preview_lines) if preview_lines else "<i>Нет готовых слов</i>"

        summary = (
            f"<b>Импорт обработан</b>\n\n"
            f"Источник: <code>{imp.filename}</code>\n"
            f"Всего слов: <b>{imp.total_words}</b> · Распознано: <b>{len(valid_words)}</b>\n"
            f"Дубликатов: <b>{len(duplicate_words)}</b> · Требуют уточнения: <b>{len(clarification_words)}</b>\n\n"
            f"<b>Предпросмотр:</b>\n{preview_text}\n\n"
            f"<i>Слова находятся на проверке и пока не добавлены в основной словарь:</i>"
        )
        return summary

    async def confirm_staged_import(
        self,
        import_id: int,
        target_dict_id: Optional[int] = None,
        custom_dict_title: Optional[str] = None,
    ) -> Tuple[int, Dictionary]:
        added_count, target_dict = await self.import_repo.confirm_import(
            import_id=import_id,
            target_dict_id=target_dict_id,
            custom_dict_title=custom_dict_title,
        )

        imp = await self.import_repo.get_by_id(import_id)
        if imp:
            await self.achievement_repo.award_achievement(imp.user_id, "IMPORT_EXPLORER")

        return added_count, target_dict

