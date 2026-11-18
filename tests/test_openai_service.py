import pytest
from unittest.mock import AsyncMock, MagicMock
from openai import RateLimitError
from learnwords.services.openai_service import OpenAIService
from learnwords.schemas.word import WordCardSchema, GeneratedWordBatch
from learnwords.schemas.ai_responses import AnswerEvaluation, StagedImportAnalysis, StagedWordItem


@pytest.mark.asyncio
async def test_openai_generate_words_mocked(monkeypatch):
    service = OpenAIService(api_key="sk-proj-testmockkey")

    mock_batch = GeneratedWordBatch(
        words=[
            WordCardSchema(
                english_word="Resilient",
                translation="Жизнестойкий, упругий",
                part_of_speech="Adjective",
                cefr_level="B2",
                topic="Personality",
                example_en="She is remarkably resilient despite difficulties.",
                example_ru="Она удивительно жизнестойка несмотря на трудности.",
                synonyms=["Tough", "Adaptable"],
                notes="Formal adjective",
            )
        ]
    )

    mock_parsed_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.parsed = mock_batch
    mock_parsed_response.choices = [mock_choice]

    mock_parse_call = AsyncMock(return_value=mock_parsed_response)
    monkeypatch.setattr(service.client.beta.chat.completions, "parse", mock_parse_call)

    words = await service.generate_words(level="B2", topic="Personality", count=1)
    assert len(words) == 1
    assert words[0].english_word == "Resilient"
    assert words[0].cefr_level == "B2"


@pytest.mark.asyncio
async def test_openai_evaluate_answer_mocked(monkeypatch):
    service = OpenAIService(api_key="sk-proj-testmockkey")

    mock_eval = AnswerEvaluation(
        is_correct=True,
        quality_score=4,
        correct_answer="Уверенный в себе",
        explanation="Отлично! Перевод передает точный смысл.",
        acceptable_alternatives=["Уверенный", "Самонадеянный"],
        memory_tip="Слово confident созвучно с конфиденциальный (тот, в ком ты уверен).",
    )

    mock_parsed_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.parsed = mock_eval
    mock_parsed_response.choices = [mock_choice]

    mock_parse_call = AsyncMock(return_value=mock_parsed_response)
    monkeypatch.setattr(service.client.beta.chat.completions, "parse", mock_parse_call)

    res = await service.evaluate_answer(
        question_type="EN_RU",
        english_word="Confident",
        target_ru="Уверенный в себе",
        user_answer="уверенный",
    )

    assert res.is_correct is True
    assert res.quality_score == 4
    assert "Уверенный" in res.acceptable_alternatives


@pytest.mark.asyncio
async def test_openai_retry_logic(monkeypatch):
    service = OpenAIService(api_key="sk-proj-testmockkey")

    mock_eval = AnswerEvaluation(
        is_correct=True,
        quality_score=5,
        correct_answer="Reliable",
        explanation="OK",
        acceptable_alternatives=[],
        memory_tip="",
    )

    mock_parsed_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.parsed = mock_eval
    mock_parsed_response.choices = [mock_choice]

    # Create dummy RateLimitError
    dummy_response = MagicMock()
    dummy_response.status_code = 429
    dummy_response.headers = {}
    rate_err = RateLimitError(
        message="Rate limit exceeded",
        response=dummy_response,
        body=None,
    )

    # Fail on first call, succeed on second
    mock_parse_call = AsyncMock(side_effect=[rate_err, mock_parsed_response])
    monkeypatch.setattr(service.client.beta.chat.completions, "parse", mock_parse_call)

    res = await service.evaluate_answer(
        question_type="RU_EN",
        english_word="Reliable",
        target_ru="Надёжный",
        user_answer="reliable",
    )

    assert res.is_correct is True
    assert mock_parse_call.call_count == 2

