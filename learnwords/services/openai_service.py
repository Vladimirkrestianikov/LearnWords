import asyncio
import json
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI, RateLimitError, APIConnectionError, APITimeoutError, APIError
from learnwords.config.settings import settings
from learnwords.utils.logger import logger
from learnwords.schemas.word import WordCardSchema, GeneratedWordBatch
from learnwords.schemas.ai_responses import (
    AnswerEvaluation,
    StagedImportAnalysis,
    StagedWordItem,
    GeneratedQuizQuestion,
)


class OpenAIService:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self._client: Optional[AsyncOpenAI] = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key if self.api_key else "missing-key",
                timeout=35.0,
            )
        return self._client

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("sk-"))

    async def _call_with_retry(self, func, *args, max_retries: int = 3, **kwargs):
        """Execute async API call with exponential backoff retry."""
        delay = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except (RateLimitError, APIConnectionError, APITimeoutError) as e:
                logger.warning(
                    f"OpenAI API call transient error on attempt {attempt}/{max_retries}: {type(e).__name__}. Retrying in {delay}s..."
                )
                if attempt == max_retries:
                    logger.error(f"OpenAI API failed after {max_retries} attempts: {e}")
                    raise
                await asyncio.sleep(delay)
                delay *= 2
            except APIError as e:
                logger.error(f"OpenAI API non-retryable error: {e}")
                raise

    async def generate_words(
        self,
        level: str,
        topic: str,
        count: int = 5,
        exclude_words: Optional[List[str]] = None,
    ) -> List[WordCardSchema]:
        """Generate high quality vocabulary items tailored to user level, topic, and exclusions."""
        if not self.is_configured():
            logger.warning("OpenAI API key not set. Using curated educational words fallback.")
            return self._fallback_words(level, topic, count, exclude_words or [])

        exclude_str = ", ".join(exclude_words[:50]) if exclude_words else "none"

        system_prompt = (
            "You are a Senior English Lexicographer and Language Coach for LearnWords.\n"
            "Your task is to select and explain natural, high-frequency English vocabulary tailored to the student's CEFR level and requested topic.\n"
            "Guidelines:\n"
            "1. Each word must match the requested CEFR level (A1 to C2).\n"
            "2. Provide accurate, idiomatic Russian translations.\n"
            "3. Example sentences must be natural, illustrative, and strictly at the learner's comprehension level.\n"
            "4. Do NOT include any of the excluded words."
        )

        user_prompt = (
            f"Generate exactly {count} distinct English vocabulary words/phrases.\n"
            f"Target CEFR Level: {level}\n"
            f"Topic: {topic}\n"
            f"Words to exclude: {exclude_str}\n"
        )

        try:
            response = await self._call_with_retry(
                self.client.beta.chat.completions.parse,
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=GeneratedWordBatch,
                temperature=0.7,
            )
            parsed: GeneratedWordBatch = response.choices[0].message.parsed
            if parsed and parsed.words:
                return parsed.words[:count]
        except Exception as e:
            logger.error(f"Error in generate_words: {e}")

        return self._fallback_words(level, topic, count, exclude_words or [])

    async def evaluate_answer(
        self,
        question_type: str,
        english_word: str,
        target_ru: str,
        user_answer: str,
        context_sentence: Optional[str] = None,
        custom_prompt: Optional[str] = None,
    ) -> AnswerEvaluation:
        """
        Evaluate student response intelligently:
        Accepts valid synonyms, alternative grammatical phrasing, and assesses semantic correctness.
        Returns quality score (0 to 5) for SM-2 spaced repetition and feedback.
        """
        if not self.is_configured():
            return self._fallback_evaluate_answer(english_word, target_ru, user_answer)

        system_prompt = (
            "You are an encouraging, expert English teacher in LearnWords evaluating a student's answer.\n"
            "IMPORTANT RULES:\n"
            "1. Do NOT require rigid, verbatim string matching! Accept synonyms, equivalent phrases, and colloquial translations if the meaning is right.\n"
            "2. Minor typos should still count as is_correct=True, but with quality_score=4 instead of 5.\n"
            "3. If wrong, explain clearly in Russian what was missed, provide the best answer, and offer a short memory mnemonic/tip.\n"
            "4. Assign quality_score between 0 and 5:\n"
            "   5: Flawless answer\n"
            "   4: Correct with minor typo or acceptable variant\n"
            "   3: Understandable but slightly awkward or partial\n"
            "   2: Incorrect but recognizable attempt\n"
            "   1: Completely wrong\n"
            "   0: Blank or nonsense"
        )

        user_content = (
            f"Task Type: {question_type}\n"
            f"English Word: {english_word}\n"
            f"Dictionary Translation: {target_ru}\n"
            f"Context / Prompt: {context_sentence or custom_prompt or 'Translate'}\n"
            f"Student Answer: '{user_answer}'\n\n"
            "Evaluate if the student understood the word and translated/used it correctly."
        )

        try:
            response = await self._call_with_retry(
                self.client.beta.chat.completions.parse,
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                response_format=AnswerEvaluation,
                temperature=0.3,
            )
            parsed: AnswerEvaluation = response.choices[0].message.parsed
            if parsed:
                return parsed
        except Exception as e:
            logger.error(f"Error evaluating answer with OpenAI: {e}")

        return self._fallback_evaluate_answer(english_word, target_ru, user_answer)

    async def analyze_raw_vocabulary(
        self, raw_text: str, default_topic: Optional[str] = None
    ) -> StagedImportAnalysis:
        """
        Parse raw user input or extracted document text into rich structured vocabulary entries.
        Cleans typos, identifies CEFR level, part of speech, creates examples and translations.
        """
        if not self.is_configured():
            return self._fallback_analyze_vocabulary(raw_text, default_topic)

        system_prompt = (
            "You are a Linguist and Vocabulary Parser for LearnWords.\n"
            "Your task is to analyze user-provided raw text or notes (from text messages, TXT, DOCX, PDF, CSV, etc.) "
            "and extract English-Russian vocabulary pairs.\n"
            "Rules:\n"
            "1. Extract the normalized English word/phrase and accurate Russian translation.\n"
            "2. Fix obvious spelling typos in English words.\n"
            "3. Identify part of speech (Noun, Verb, Adjective, Adverb, Idiom, Phrasal verb).\n"
            "4. Estimate CEFR level (A1 to C2).\n"
            "5. Generate a natural English example sentence with Russian translation.\n"
            "6. Mark is_ambiguous=True if the translation is questionable or incomplete.\n"
            "7. Return clean, deduplicated structured items."
        )

        user_prompt = (
            f"Raw vocabulary text to process:\n\"\"\"\n{raw_text[:4000]}\n\"\"\"\n"
            f"Default Topic hint: {default_topic or 'General'}\n"
        )

        try:
            response = await self._call_with_retry(
                self.client.beta.chat.completions.parse,
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=StagedImportAnalysis,
                temperature=0.4,
            )
            parsed: StagedImportAnalysis = response.choices[0].message.parsed
            if parsed and parsed.words:
                return parsed
        except Exception as e:
            logger.error(f"Error analyzing raw vocabulary with OpenAI: {e}")

        return self._fallback_analyze_vocabulary(raw_text, default_topic)

    # Fallback offline helpers for resilience
    def _fallback_words(
        self, level: str, topic: str, count: int, exclude: List[str]
    ) -> List[WordCardSchema]:
        curated_db = [
            WordCardSchema(
                english_word="Confident",
                translation="Уверенный в себе",
                part_of_speech="Adjective",
                cefr_level=level,
                topic=topic,
                example_en="She feels confident about her upcoming interview.",
                example_ru="Она чувствует уверенность перед предстоящим собеседованием.",
                synonyms=["Self-assured", "Certain", "Positive"],
                notes="Часто используется с предлогом about или in.",
            ),
            WordCardSchema(
                english_word="Anxious",
                translation="Встревоженный, беспокойный",
                part_of_speech="Adjective",
                cefr_level=level,
                topic=topic,
                example_en="He was anxious about the test results.",
                example_ru="Он тревожился о результатах теста.",
                synonyms=["Worried", "Apprehensive", "Uneasy"],
                notes="Может означать как сильное беспокойство, так и нетерпеливое ожидание (anxious to see you).",
            ),
            WordCardSchema(
                english_word="Exhausted",
                translation="Истощённый, очень уставший",
                part_of_speech="Adjective",
                cefr_level=level,
                topic=topic,
                example_en="I felt completely exhausted after working all day.",
                example_ru="Я чувствовал себя совершенно истощённым после работы весь день.",
                synonyms=["Extremely tired", "Drained", "Worn out"],
                notes="Extreme adjective: обычно не используется со словом very, лучше absolutely exhausted.",
            ),
            WordCardSchema(
                english_word="Opportunity",
                translation="Возможность, удобный случай",
                part_of_speech="Noun",
                cefr_level=level,
                topic=topic,
                example_en="This new job is a wonderful opportunity for professional growth.",
                example_ru="Эта новая работа — замечательная возможность для профессионального роста.",
                synonyms=["Chance", "Possibility", "Opening"],
                notes="Колликация: seize the opportunity (воспользоваться возможностью).",
            ),
            WordCardSchema(
                english_word="Reliable",
                translation="Надёжный",
                part_of_speech="Adjective",
                cefr_level=level,
                topic=topic,
                example_en="He is a reliable friend who always keeps his promises.",
                example_ru="Он надёжный друг, который всегда держит свои обещания.",
                synonyms=["Dependable", "Trustworthy", "Solid"],
                notes="Происходит от глагола rely (полагаться).",
            ),
            WordCardSchema(
                english_word="Overcome",
                translation="Преодолевать, справляться",
                part_of_speech="Verb",
                cefr_level=level,
                topic=topic,
                example_en="She learned to overcome her fear of public speaking.",
                example_ru="Она научилась преодолевать свой страх публичных выступлений.",
                synonyms=["Conquer", "Surmount", "Defeat"],
                notes="Неправильный глагол: overcome - overcame - overcome.",
            ),
            WordCardSchema(
                english_word="Inspire",
                translation="Вдохновлять",
                part_of_speech="Verb",
                cefr_level=level,
                topic=topic,
                example_en="His passion for music inspires everyone around him.",
                example_ru="Его страсть к музыке вдохновляет всех вокруг.",
                synonyms=["Motivate", "Encourage", "Stimulate"],
                notes="Существительное: inspiration.",
            ),
        ]
        exclude_lower = {w.lower() for w in exclude}
        results = [w for w in curated_db if w.english_word.lower() not in exclude_lower]
        if not results:
            results = curated_db
        return results[:count]

    def _fallback_evaluate_answer(
        self, english_word: str, target_ru: str, user_answer: str
    ) -> AnswerEvaluation:
        norm_user = user_answer.strip().lower()
        norm_target = target_ru.strip().lower()
        norm_en = english_word.strip().lower()

        is_match = (
            norm_user == norm_target
            or norm_user == norm_en
            or norm_user in norm_target
            or norm_target in norm_user
        )

        if is_match:
            return AnswerEvaluation(
                is_correct=True,
                quality_score=5,
                correct_answer=target_ru,
                explanation="Отлично! Перевод выполнен верно.",
                acceptable_alternatives=[target_ru, english_word],
                memory_tip=f"Слово '{english_word}' отлично закреплено в вашей памяти!",
            )
        else:
            return AnswerEvaluation(
                is_correct=False,
                quality_score=1,
                correct_answer=target_ru,
                explanation=f"Ваш ответ '{user_answer}' отличается от правильного перевода '{target_ru}'.",
                acceptable_alternatives=[target_ru],
                memory_tip=f"Повторите вслух: {english_word} — {target_ru}.",
            )

    def _fallback_analyze_vocabulary(
        self, raw_text: str, default_topic: Optional[str]
    ) -> StagedImportAnalysis:
        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        words = []
        for line in lines:
            parts = None
            for sep in ["—", "-", ":", "=", "\t"]:
                if sep in line:
                    parts = line.split(sep, 1)
                    break
            if parts and len(parts) == 2:
                en = parts[0].strip()
                ru = parts[1].strip()
                words.append(
                    StagedWordItem(
                        english_word=en.capitalize(),
                        translation=ru,
                        part_of_speech="Word",
                        cefr_level="B1",
                        topic=default_topic or "Imported",
                        example_en=f"We should remember the word '{en}'.",
                        example_ru=f"Нам следует запомнить слово '{ru}'.",
                        synonyms=[],
                        is_ambiguous=False,
                    )
                )

        return StagedImportAnalysis(
            words=words,
            total_recognized=len(words),
            summary=f"Распознано {len(words)} пар слов из загруженного текста.",
        )

