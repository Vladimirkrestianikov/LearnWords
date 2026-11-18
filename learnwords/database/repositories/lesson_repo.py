import json
import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, update, func, and_, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from learnwords.database.models import Lesson, TestAttempt, Word


class LessonRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_lesson(
        self,
        user_id: int,
        topic: Optional[str],
        level: Optional[str],
        word_ids: List[int],
    ) -> Lesson:
        lesson = Lesson(
            user_id=user_id,
            topic=topic,
            level=level,
            total_words=len(word_ids),
            correct_answers=0,
            incorrect_answers=0,
            completed=False,
            current_index=0,
            word_ids=json.dumps(word_ids),
            created_at=datetime.datetime.now(),
        )
        self.session.add(lesson)
        await self.session.commit()
        await self.session.refresh(lesson)
        return lesson

    async def get_by_id(self, lesson_id: int) -> Optional[Lesson]:
        stmt = select(Lesson).where(Lesson.id == lesson_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_lesson(self, user_id: int) -> Optional[Lesson]:
        stmt = (
            select(Lesson)
            .where(
                and_(
                    Lesson.user_id == user_id,
                    Lesson.completed == False,
                )
            )
            .order_by(Lesson.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def record_attempt(
        self,
        user_id: int,
        word_id: int,
        question_type: str,
        user_answer: str,
        correct_answer: str,
        is_correct: bool,
        lesson_id: Optional[int] = None,
        ai_feedback: Optional[Dict[str, Any]] = None,
    ) -> TestAttempt:
        feedback_json = json.dumps(ai_feedback, ensure_ascii=False) if ai_feedback else None
        attempt = TestAttempt(
            user_id=user_id,
            word_id=word_id,
            lesson_id=lesson_id,
            question_type=question_type,
            user_answer=user_answer,
            correct_answer=correct_answer,
            is_correct=is_correct,
            ai_feedback=feedback_json,
            created_at=datetime.datetime.now(),
        )
        self.session.add(attempt)

        if lesson_id:
            lesson = await self.get_by_id(lesson_id)
            if lesson:
                if is_correct:
                    lesson.correct_answers += 1
                else:
                    lesson.incorrect_answers += 1
                lesson.current_index += 1

        await self.session.commit()
        await self.session.refresh(attempt)
        return attempt

    async def complete_lesson(self, lesson_id: int) -> Optional[Lesson]:
        lesson = await self.get_by_id(lesson_id)
        if lesson:
            lesson.completed = True
            lesson.completed_at = datetime.datetime.now()
            await self.session.commit()
            await self.session.refresh(lesson)
        return lesson

    async def get_user_performance(
        self, user_id: int, days: Optional[int] = None
    ) -> Dict[str, Any]:
        """Aggregate test attempts: total, correct, incorrect, accuracy %."""
        stmt = select(
            func.count(TestAttempt.id),
            func.sum(case((TestAttempt.is_correct == True, 1), else_=0)),
            func.sum(case((TestAttempt.is_correct == False, 1), else_=0)),
        ).where(TestAttempt.user_id == user_id)

        if days is not None:
            cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
            stmt = stmt.where(TestAttempt.created_at >= cutoff)

        result = await self.session.execute(stmt)
        total, correct, incorrect = result.first()
        total = total or 0
        correct = correct or 0
        incorrect = incorrect or 0
        accuracy = round((correct / total * 100), 1) if total > 0 else 0.0

        # Completed lessons count
        lessons_stmt = select(func.count(Lesson.id)).where(
            and_(
                Lesson.user_id == user_id,
                Lesson.completed == True,
            )
        )
        if days is not None:
            cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
            lessons_stmt = lessons_stmt.where(Lesson.created_at >= cutoff)
        completed_lessons = (await self.session.execute(lessons_stmt)).scalar() or 0

        return {
            "total_attempts": total,
            "correct": correct,
            "incorrect": incorrect,
            "accuracy": accuracy,
            "completed_lessons": completed_lessons,
        }

    async def get_topic_stats(self, user_id: int) -> List[Dict[str, Any]]:
        """Performance broken down by topic."""
        stmt = (
            select(
                Word.topic,
                func.count(TestAttempt.id).label("total"),
                func.sum(case((TestAttempt.is_correct == True, 1), else_=0)).label("correct"),
            )
            .join(Word, TestAttempt.word_id == Word.id)
            .where(TestAttempt.user_id == user_id)
            .group_by(Word.topic)
            .having(func.count(TestAttempt.id) >= 2)
        )
        result = await self.session.execute(stmt)
        topic_stats = []
        for row in result.all():
            topic = row[0] or "General"
            total = row[1]
            correct = row[2] or 0
            accuracy = round((correct / total * 100), 1) if total > 0 else 0.0
            topic_stats.append({
                "topic": topic,
                "total": total,
                "correct": correct,
                "accuracy": accuracy,
            })
        topic_stats.sort(key=lambda x: x["accuracy"], reverse=True)
        return topic_stats

    async def get_weak_words(self, user_id: int, limit: int = 5) -> List[Tuple[Word, int, int]]:
        """Find words where user has highest error rate."""
        stmt = (
            select(
                Word,
                func.sum(case((TestAttempt.is_correct == False, 1), else_=0)).label("errors"),
                func.count(TestAttempt.id).label("total"),
            )
            .join(Word, TestAttempt.word_id == Word.id)
            .where(TestAttempt.user_id == user_id)
            .group_by(Word.id)
            .having(func.sum(case((TestAttempt.is_correct == False, 1), else_=0)) > 0)
            .order_by(desc("errors"))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1], row[2]) for row in result.all()]
