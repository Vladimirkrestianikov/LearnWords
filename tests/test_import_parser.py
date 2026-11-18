import io
import csv
import openpyxl
import docx
import pytest
from unittest.mock import MagicMock, AsyncMock
from learnwords.schemas.ai_responses import StagedImportAnalysis, StagedWordItem
from learnwords.utils.file_parser import FileParser
from learnwords.utils.validators import validate_file_upload
from learnwords.services.import_service import ImportService
from learnwords.database.repositories.user_repo import UserRepository
from learnwords.database.repositories.dictionary_repo import DictionaryRepository
from learnwords.database.repositories.word_repo import WordRepository


def test_file_parser_txt():
    sample = "Confident — Уверенный\nAnxious — Встревоженный"
    res = FileParser.extract_text(sample.encode("utf-8"), "words.txt")
    assert "Confident" in res
    assert "Anxious" in res


def test_file_parser_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Brave", "Храбрый"])
    writer.writerow(["Humble", "Скромный"])
    res = FileParser.extract_text(output.getvalue().encode("utf-8"), "list.csv")
    assert "Brave — Храбрый" in res
    assert "Humble — Скромный" in res


def test_file_parser_docx():
    doc = docx.Document()
    doc.add_paragraph("Delighted — Очень довольный")
    stream = io.BytesIO()
    doc.save(stream)
    res = FileParser.extract_text(stream.getvalue(), "doc.docx")
    assert "Delighted — Очень довольный" in res


def test_file_parser_xlsx():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Exhausted", "Очень уставший"])
    stream = io.BytesIO()
    wb.save(stream)
    res = FileParser.extract_text(stream.getvalue(), "table.xlsx")
    assert "Exhausted — Очень уставший" in res


def test_validator_file_upload():
    valid, _ = validate_file_upload("test.pdf", 1024)
    assert valid is True

    invalid_ext, msg = validate_file_upload("test.exe", 1024)
    assert invalid_ext is False
    assert "Неподдерживаемый формат" in msg

    too_large, msg_large = validate_file_upload("huge.pdf", 50 * 1024 * 1024)
    assert too_large is False
    assert "превышает лимит" in msg_large


@pytest.mark.asyncio
async def test_staged_import_lifecycle(test_session):
    user_repo = UserRepository(test_session)
    user, _ = await user_repo.create_or_get_user(telegram_id=55555)

    word_repo = WordRepository(test_session)
    # Pre-add an existing word to trigger duplicate detection
    await word_repo.get_or_create_word(english_word="ExistingWord", translation="Существующее")

    mock_ai = MagicMock()
    mock_ai.analyze_raw_vocabulary = AsyncMock(return_value=StagedImportAnalysis(
        words=[
            StagedWordItem(english_word="ExistingWord", translation="Существующее", is_ambiguous=False),
            StagedWordItem(english_word="NewWord", translation="Новое слово", is_ambiguous=False),
            StagedWordItem(english_word="AmbiguousWord", translation="?", is_ambiguous=True),
        ],
        total_recognized=3,
        summary="Test analysis",
    ))
    import_service = ImportService(test_session, openai_service=mock_ai)
    raw_sample = (
        "ExistingWord — Существующее\n"
        "NewWord — Новое слово\n"
        "AmbiguousWord — ?"
    )

    # Stage import (must NOT be added to main vocabulary immediately)
    imp = await import_service.stage_import_from_text(
        user_id=user.id,
        raw_text=raw_sample,
        filename="test_notes.txt"
    )

    assert imp.status == "PENDING_VERIFICATION"
    words = await import_service.import_repo.get_words(imp.id)
    assert len(words) == 3

    statuses = {w.english_word.lower(): w.status for w in words}
    assert statuses.get("existingword") == "DUPLICATE"
    assert statuses.get("ambiguousword") == "NEEDS_CLARIFICATION"
    assert statuses.get("newword") == "VALID"

    # Confirm staged import
    added_count, target_dict = await import_service.confirm_staged_import(imp.id)
    assert added_count >= 1
    assert target_dict is not None

    confirmed_imp = await import_service.import_repo.get_by_id(imp.id)
    assert confirmed_imp.status == "CONFIRMED"

    # Verify newly confirmed word is now searchable in dictionary
    dict_repo = DictionaryRepository(test_session)
    dict_words = await dict_repo.get_words_in_dictionary(target_dict.id)
    dict_en = [w.english_word.lower() for w in dict_words]
    assert "newword" in dict_en

