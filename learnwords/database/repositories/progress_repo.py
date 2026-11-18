import datetime
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy import select, update, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from learnwords.database.models import (
    WordProgress,
    WordProgressStatus,
    Word,
    TestAttempt,
)
from learnwords.utils.sm2 import calculate_sm2


class ProgressRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_progress(self, user_id: int, word_id: int) -> Optional[WordProgress]:
        stmt = (
            select(WordProgress)
            .options(selectinload(WordProgress.word))
            .where(
                and_(
                    WordProgress.user_id == user_id,
                    WordProgress.word_id == word_id,
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_progress(self, user_id: int, word_id: int) -> WordProgress:
        prog = await self.get_progress(user_id, word_id)
        if not prog:
            prog = WordProgress(
                user_id=user_id,
                word_id=word_id,
                status=WordProgressStatus.NEW,
                repetitions=0,
                correct_answers=0,
                incorrect_answers=0,
                ease_factor=2.5,
                interval_days=0.0,
                next_review_at=None,
                last_review_at=None,
                is_favorite=False,
            )
            self.session.add(prog)
            await self.session.commit()
            await self.session.refresh(prog, attribute_names=["word"])
        return prog

    async def record_review(
        self,
        user_id: int,
        word_id: int,
        is_correct: bool,
        quality: int = 4,
    ) -> WordProgress:
        """Update SM-2 parameters for a word after a test/review."""
        prog = await self.get_or_create_progress(user_id, word_id)
        now = datetime.datetime.now()

        if is_correct:
            prog.correct_answers += 1
            if quality < 3:
                quality = 4
        else:
            prog.incorrect_answers += 1
            if quality >= 3:
                quality = 1

        sm2_res = calculate_sm2(
            repetitions=prog.repetitions,
            ease_factor=prog.ease_factor,
            interval_days=prog.interval_days,
            quality=quality,
            now=now,
        )

        prog.repetitions = sm2_res.repetitions
        prog.ease_factor = sm2_res.ease_factor
        prog.interval_days = sm2_res.interval_days
        prog.next_review_at = sm2_res.next_review_at
        prog.status = sm2_res.status
        prog.last_review_at = now

        await self.session.commit()
        await self.session.refresh(prog, attribute_names=["word"])
        return prog

    async def mark_as_known(self, user_id: int, word_id: int) -> WordProgress:
        """User marks word as 'I already know this'."""
        prog = await self.get_or_create_progress(user_id, word_id)
        now = datetime.datetime.now()
        prog.status = WordProgressStatus.MASTERED
        prog.repetitions = 5
        prog.ease_factor = 2.5
        prog.interval_days = 30.0
        prog.next_review_at = now + datetime.timedelta(days=30)
        prog.last_review_at = now
        await self.session.commit()
        await self.session.refresh(prog, attribute_names=["word"])
        return prog

    async def mark_as_difficult(self, user_id: int, word_id: int) -> WordProgress:
        """User marks word as 'Hard to remember'."""
        prog = await self.get_or_create_progress(user_id, word_id)
        now = datetime.datetime.now()
        prog.status = WordProgressStatus.DIFFICULT
        prog.repetitions = 0
        prog.ease_factor = max(1.3, prog.ease_factor - 0.2)
        prog.interval_days = 0.007
        prog.next_review_at = now + datetime.timedelta(minutes=10)
        prog.last_review_at = now
        await self.session.commit()
        await self.session.refresh(prog, attribute_names=["word"])
        return prog

    async def toggle_favorite(self, user_id: int, word_id: int) -> bool:
        prog = await self.get_or_create_progress(user_id, word_id)
        prog.is_favorite = not prog.is_favorite
        await self.session.commit()
        return prog.is_favorite

    async def get_words_for_review(
        self, user_id: int, limit: int = 15
    ) -> List[Tuple[WordProgress, Word]]:
        now = datetime.datetime.now()
        stmt = (
            select(WordProgress, Word)
            .join(Word, WordProgress.word_id == Word.id)
            .where(
                and_(
                    WordProgress.user_id == user_id,
                    or_(
                        WordProgress.next_review_at <= now,
                        WordProgress.status.in_([
                            WordProgressStatus.NEEDS_REVIEW,
                            WordProgressStatus.DIFFICULT,
                        ]),
                    ),
                )
            )
            .order_by(WordProgress.next_review_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_difficult_words(
        self, user_id: int, limit: int = 20
    ) -> List[Tuple[WordProgress, Word]]:
        stmt = (
            select(WordProgress, Word)
            .join(Word, WordProgress.word_id == Word.id)
            .where(
                and_(
                    WordProgress.user_id == user_id,
                    or_(
                        WordProgress.status == WordProgressStatus.DIFFICULT,
                        WordProgress.incorrect_answers > WordProgress.correct_answers,
                    ),
                )
            )
            .order_by(desc(WordProgress.incorrect_answers))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_review_counts(self, user_id: int) -> Dict[str, int]:
        now = datetime.datetime.now()
        # total learned
        learned_stmt = select(func.count(WordProgress.id)).where(
            WordProgress.user_id == user_id
        )
        # waiting review (due now)
        due_stmt = select(func.count(WordProgress.id)).where(
            and_(
                WordProgress.user_id == user_id,
                WordProgress.next_review_at <= now,
            )
        )
        # overdue (more than 1 day overdue)
        overdue_stmt = select(func.count(WordProgress.id)).where(
            and_(
                WordProgress.user_id == user_id,
                WordProgress.next_review_at <= now - datetime.timedelta(days=1),
            )
        )
        # learning
        learning_stmt = select(func.count(WordProgress.id)).where(
            and_(
                WordProgress.user_id == user_id,
                WordProgress.status.in_([
                    WordProgressStatus.LEARNING,
                    WordProgressStatus.FAMILIAR,
                ]),
            )
        )
        # mastered
        mastered_stmt = select(func.count(WordProgress.id)).where(
            and_(
                WordProgress.user_id == user_id,
                WordProgress.status == WordProgressStatus.MASTERED,
            )
        )
        # difficult
        difficult_stmt = select(func.count(WordProgress.id)).where(
            and_(
                WordProgress.user_id == user_id,
                WordProgress.status == WordProgressStatus.DIFFICULT,
            )
        )

        total_learned = (await self.session.execute(learned_stmt)).scalar() or 0
        due = (await self.session.execute(due_stmt)).scalar() or 0
        overdue = (await self.session.execute(overdue_stmt)).scalar() or 0
        learning = (await self.session.execute(learning_stmt)).scalar() or 0
        mastered = (await self.session.execute(mastered_stmt)).scalar() or 0
        difficult = (await self.session.execute(difficult_stmt)).scalar() or 0

        return {
            "total_learned": total_learned,
            "due": due,
            "overdue": overdue,
            "learning": learning,
            "mastered": mastered,
            "difficult": difficult,
        }

    async def get_studied_word_ids(self, user_id: int) -> List[int]:
        stmt = select(WordProgress.word_id).where(WordProgress.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

