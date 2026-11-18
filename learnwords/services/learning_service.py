import html
import json
import random
import re
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from learnwords.database.models import Word, Lesson, TestAttempt, WordProgress
from learnwords.database.repositories.word_repo import WordRepository
from learnwords.database.repositories.lesson_repo import LessonRepository
from learnwords.database.repositories.progress_repo import ProgressRepository
from learnwords.database.repositories.user_repo import UserRepository
from learnwords.database.repositories.achievement_repo import AchievementRepository
from learnwords.services.openai_service import OpenAIService
from learnwords.services.vocabulary_service import VocabularyService
from learnwords.schemas.ai_responses import AnswerEvaluation


class LearningService:
    QUESTION_TYPES = [
        "EN_RU",
        "RU_EN",
        "CHOICE",
        "FILL_BLANK",
        "MAKE_SENTENCE",
        "SENTENCE_TRANSLATION",
        "CONTEXT_DEFINITION",
    ]

    # Shown on the first card of a lesson so the buttons are clear
    CARD_LEGEND = (
        "<i>Знаю — слово известно, больше не показывать\n"
        "Сложное — повторять чаще\n"
        "☆ — добавить в избранное\n"
        "Тест — сразу проверить себя на этом слове\n"
        "Далее → — следующее слово</i>"
    )

    def __init__(self, session: AsyncSession, openai_service: Optional[OpenAIService] = None):
        self.session = session
        self.word_repo = WordRepository(session)
        self.lesson_repo = LessonRepository(session)
        self.progress_repo = ProgressRepository(session)
        self.user_repo = UserRepository(session)
        self.achievement_repo = AchievementRepository(session)
        self.openai_service = openai_service or OpenAIService()
        self.vocabulary_service = VocabularyService(session, self.openai_service)

    async def start_lesson(self, user_id: int) -> Tuple[Lesson, List[Word]]:
        """Start a new learning session for user based on settings."""
        user = await self.user_repo.get_by_id(user_id)
        settings = user.settings

        # Determine batch count (usually 5 words per mini-lesson chunk)
        count = min(settings.daily_word_goal, 5)
        words = await self.vocabulary_service.get_or_generate_words_for_learning(
            user_id=user_id,
            settings=settings,
            count=count,
        )

        word_ids = [w.id for w in words]
        lesson = await self.lesson_repo.create_lesson(
            user_id=user_id,
            topic=words[0].topic if words else "General",
            level=settings.english_level,
            word_ids=word_ids,
        )

        return lesson, words

    @staticmethod
    def _format_synonyms(raw: Optional[str]) -> str:
        """Synonyms are stored either as a JSON list or as a comma-separated string."""
        if not raw:
            return ""
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return ", ".join(str(x) for x in parsed if x)
        except (ValueError, TypeError):
            pass
        return raw

    @staticmethod
    def _highlight(sentence: str, word: str) -> str:
        """Escape a sentence and make the studied word bold inside it."""
        escaped = html.escape(sentence)
        target = html.escape(word)
        if not target:
            return escaped
        return re.sub(
            rf"\b({re.escape(target)}\w*)",
            r"<b>\1</b>",
            escaped,
            flags=re.IGNORECASE,
        )

    async def format_word_card(self, word: Word, index: int, total: int, is_favorite: bool = False) -> str:
        """
        Word card with a clear text hierarchy:
          1. progress line (small, secondary)
          2. the English word: bold + underlined, on its own line
          3. part of speech / level / topic (italic, secondary)
          4. translation (bold)
          5. example in a quote block with the word highlighted
          6. optional synonyms / notes
        """
        en = html.escape(word.english_word)
        translation = html.escape(word.translation)
        pos = html.escape((word.part_of_speech or "").lower())
        level = html.escape(word.cefr_level or "")
        topic = html.escape(word.topic or "")
        meta_line = " · ".join(part for part in (pos, level, topic) if part)

        fav_mark = "  ★" if is_favorite else ""

        lines = [
            f"<i>Слово {index} из {total}</i>",
            "",
            f"<b><u>{en}</u></b>{fav_mark}",
        ]
        if meta_line:
            lines.append(f"<i>{meta_line}</i>")
        lines += ["", f"<b>{translation}</b>"]

        if word.example_en:
            example = self._highlight(word.example_en, word.english_word)
            if word.example_ru:
                example += f"\n<i>{html.escape(word.example_ru)}</i>"
            lines += ["", f"<blockquote>{example}</blockquote>"]

        synonyms = self._format_synonyms(word.synonyms)
        if synonyms:
            lines += ["", f"Синонимы: <i>{html.escape(synonyms)}</i>"]
        if word.notes:
            lines.append(f"Заметка: <i>{html.escape(word.notes)}</i>")

        if index == 1:
            lines += ["", self.CARD_LEGEND]
        if index == total:
            lines += ["", "<i>Это последнее слово. «Далее →» начнёт короткий тест по словам урока.</i>"]

        return "\n".join(lines)

    async def generate_test_question(
        self,
        word: Word,
        question_type: Optional[str] = None,
        other_words: Optional[List[Word]] = None,
    ) -> Dict[str, Any]:
        """Generate one of the 7 interactive question types with clean formatting."""
        if not question_type:
            question_type = random.choice(self.QUESTION_TYPES)

        data = {
            "question_type": question_type,
            "word_id": word.id,
            "english_word": word.english_word,
            "translation": word.translation,
        }

        en = html.escape(word.english_word)
        ru = html.escape(word.translation)
        if question_type == "EN_RU":
            data["prompt"] = (
                f"<b><u>{en}</u></b>\n\n"
                f"<i>Напишите перевод на русский язык:</i>"
            )
            data["correct_answer"] = word.translation

        elif question_type == "RU_EN":
            data["prompt"] = (
                f"<b><u>{ru}</u></b>\n\n"
                f"<i>Напишите это слово на английском:</i>"
            )
            data["correct_answer"] = word.english_word

        elif question_type == "CHOICE":
            distractors = ["Happy", "Quiet", "Important", "Notice", "Difficult", "Interesting"]
            if other_words:
                pool = [w.translation for w in other_words if w.id != word.id]
                if pool:
                    distractors = pool

            options = [word.translation]
            for d in distractors:
                if d not in options and len(options) < 4:
                    options.append(d)
            while len(options) < 4:
                options.append(f"Вариант {len(options)+1}")
            random.shuffle(options)

            data["options"] = options
            data["correct_answer"] = word.translation
            data["prompt"] = (
                f"<b><u>{en}</u></b>\n\n"
                f"<i>Выберите верный перевод:</i>"
            )

        elif question_type == "FILL_BLANK":
            example = word.example_en or f"She is very {word.english_word} today."
            blank_sentence = re.sub(
                re.escape(html.escape(word.english_word)),
                "______",
                html.escape(example),
                flags=re.IGNORECASE,
            )
            data["prompt"] = (
                f"<blockquote>{blank_sentence}</blockquote>\n\n"
                f"Подсказка: <b>{ru}</b>\n"
                f"<i>Вставьте пропущенное слово:</i>"
            )
            data["correct_answer"] = word.english_word
            data["context_sentence"] = example

        elif question_type == "MAKE_SENTENCE":
            data["prompt"] = (
                f"<b><u>{en}</u></b>\n"
                f"{ru}\n\n"
                f"<i>Составьте предложение на английском с этим словом:</i>"
            )
            data["correct_answer"] = word.english_word

        elif question_type == "SENTENCE_TRANSLATION":
            example_ru = word.example_ru or f"Она была {word.translation} вчера."
            data["prompt"] = (
                f"<blockquote>{html.escape(example_ru)}</blockquote>\n\n"
                f"Используйте слово: <b><u>{en}</u></b>\n"
                f"<i>Переведите предложение на английский:</i>"
            )
            data["correct_answer"] = word.example_en or word.english_word
            data["context_sentence"] = example_ru

        elif question_type == "CONTEXT_DEFINITION":
            example = word.example_en or f"His {word.english_word} attitude was noticeable."
            data["prompt"] = (
                f"<blockquote>{self._highlight(example, word.english_word)}</blockquote>\n\n"
                f"<i>Что означает слово</i> <b><u>{en}</u></b> <i>в этом предложении?</i>"
            )
            data["correct_answer"] = word.translation
            data["context_sentence"] = example

        return data

    async def evaluate_and_record_answer(
        self,
        user_id: int,
        word: Word,
        question_type: str,
        user_answer: str,
        correct_answer: str,
        lesson_id: Optional[int] = None,
        context_sentence: Optional[str] = None,
    ) -> Tuple[AnswerEvaluation, int, List[str]]:
        """Evaluate response with OpenAIService, record and update SM-2."""
        evaluation = await self.openai_service.evaluate_answer(
            question_type=question_type,
            english_word=word.english_word,
            target_ru=word.translation,
            user_answer=user_answer,
            context_sentence=context_sentence,
        )

        # Record test attempt
        await self.lesson_repo.record_attempt(
            user_id=user_id,
            word_id=word.id,
            question_type=question_type,
            user_answer=user_answer,
            correct_answer=correct_answer,
            is_correct=evaluation.is_correct,
            lesson_id=lesson_id,
            ai_feedback={
                "explanation": evaluation.explanation,
                "memory_tip": evaluation.memory_tip,
                "acceptable_alternatives": evaluation.acceptable_alternatives,
                "quality_score": evaluation.quality_score,
            },
        )

        # Update SM-2 spaced repetition
        await self.progress_repo.record_review(
            user_id=user_id,
            word_id=word.id,
            is_correct=evaluation.is_correct,
            quality=evaluation.quality_score,
        )

        # Gamification: award XP
        earned_xp = 15 if evaluation.is_correct else 3
        _, _, leveled_up = await self.user_repo.add_xp(user_id, earned_xp)
        await self.user_repo.update_streak(user_id)

        # Check achievements
        unlocked_achievements = []
        if evaluation.is_correct:
            ach1 = await self.achievement_repo.award_achievement(user_id, "FIRST_WORD")
            if ach1:
                unlocked_achievements.append(ach1.title)

            studied_count = len(await self.progress_repo.get_studied_word_ids(user_id))
            if studied_count >= 50:
                ach50 = await self.achievement_repo.award_achievement(user_id, "FIRST_50_WORDS")
                if ach50:
                    unlocked_achievements.append(ach50.title)
            if studied_count >= 500:
                ach500 = await self.achievement_repo.award_achievement(user_id, "VOCABULARY_MASTER")
                if ach500:
                    unlocked_achievements.append(ach500.title)

        return evaluation, earned_xp, unlocked_achievements
