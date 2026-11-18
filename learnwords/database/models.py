import datetime
from typing import Optional, List
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
    func
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from learnwords.database.database import Base


class UserRole:
    ADMIN = "ADMIN"
    STUDENT = "STUDENT"


class UserStatus:
    ACTIVE = "ACTIVE"
    BANNED = "BANNED"


class WordProgressStatus:
    NEW = "NEW"
    LEARNING = "LEARNING"
    FAMILIAR = "FAMILIAR"
    MASTERED = "MASTERED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    DIFFICULT = "DIFFICULT"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.STUDENT, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=UserStatus.ACTIVE, nullable=False)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_streak_date: Mapped[Optional[datetime.date]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    last_activity: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    settings: Mapped[Optional["UserSettings"]] = relationship(
        "UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    dictionaries: Mapped[List["Dictionary"]] = relationship(
        "Dictionary", back_populates="user", cascade="all, delete-orphan"
    )
    word_progress: Mapped[List["WordProgress"]] = relationship(
        "WordProgress", back_populates="user", cascade="all, delete-orphan"
    )
    lessons: Mapped[List["Lesson"]] = relationship(
        "Lesson", back_populates="user", cascade="all, delete-orphan"
    )
    test_attempts: Mapped[List["TestAttempt"]] = relationship(
        "TestAttempt", back_populates="user", cascade="all, delete-orphan"
    )
    user_achievements: Mapped[List["UserAchievement"]] = relationship(
        "UserAchievement", back_populates="user", cascade="all, delete-orphan"
    )
    imports: Mapped[List["Import"]] = relationship(
        "Import", back_populates="user", cascade="all, delete-orphan"
    )


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    english_level: Mapped[str] = mapped_column(String(10), default="B1", nullable=False)
    preferred_topics: Mapped[str] = mapped_column(
        Text, default='["Everyday Life", "Emotions"]', nullable=False
    )
    custom_topic: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    daily_word_goal: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(50), default="STANDARD", nullable=False)
    explanation_language: Mapped[str] = mapped_column(String(20), default="RU", nullable=False)
    learning_mode: Mapped[str] = mapped_column(String(50), default="NEW_WORDS", nullable=False)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reminder_time: Mapped[str] = mapped_column(String(10), default="10:00", nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="settings")


class Word(Base):
    __tablename__ = "words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    english_word: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    translation: Mapped[str] = mapped_column(String(255), nullable=False)
    part_of_speech: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cefr_level: Mapped[Optional[str]] = mapped_column(String(10), index=True, nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    example_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    example_ru: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    synonyms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON or comma-separated
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    dictionary_words: Mapped[List["DictionaryWord"]] = relationship(
        "DictionaryWord", back_populates="word", cascade="all, delete-orphan"
    )
    progress_entries: Mapped[List["WordProgress"]] = relationship(
        "WordProgress", back_populates="word", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_words_english_topic", "english_word", "topic"),
    )


class Dictionary(Base):
    __tablename__ = "dictionaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dictionary_type: Mapped[str] = mapped_column(String(50), default="USER", nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="dictionaries")
    dictionary_words: Mapped[List["DictionaryWord"]] = relationship(
        "DictionaryWord", back_populates="dictionary", cascade="all, delete-orphan"
    )


class DictionaryWord(Base):
    __tablename__ = "dictionary_words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dictionary_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("dictionaries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    word_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("words.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    dictionary: Mapped["Dictionary"] = relationship("Dictionary", back_populates="dictionary_words")
    word: Mapped["Word"] = relationship("Word", back_populates="dictionary_words")

    __table_args__ = (
        UniqueConstraint("dictionary_id", "word_id", name="uq_dict_word"),
    )


class WordProgress(Base):
    __tablename__ = "word_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    word_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("words.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(50), default=WordProgressStatus.NEW, nullable=False)
    repetitions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    incorrect_answers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    interval_days: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    next_review_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, index=True, nullable=True)
    last_review_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="word_progress")
    word: Mapped["Word"] = relationship("Word", back_populates="progress_entries")

    __table_args__ = (
        UniqueConstraint("user_id", "word_id", name="uq_user_word_progress"),
    )


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    level: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    total_words: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    incorrect_answers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    current_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    word_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="lessons")
    attempts: Mapped[List["TestAttempt"]] = relationship("TestAttempt", back_populates="lesson")


class TestAttempt(Base):
    __tablename__ = "test_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    word_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("words.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lesson_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True, index=True
    )
    question_type: Mapped[str] = mapped_column(String(50), nullable=False)
    user_answer: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ai_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON details
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), index=True, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="test_attempts")
    lesson: Mapped[Optional["Lesson"]] = relationship("Lesson", back_populates="attempts")
    word: Mapped["Word"] = relationship("Word")


class Import(Base):
    __tablename__ = "imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING_VERIFICATION", nullable=False)
    target_dictionary_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("dictionaries.id", ondelete="SET NULL"), nullable=True
    )
    total_words: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_words: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_words: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    needs_clarification_words: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="imports")
    words: Mapped[List["ImportWord"]] = relationship(
        "ImportWord", back_populates="import_session", cascade="all, delete-orphan"
    )


class ImportWord(Base):
    __tablename__ = "import_words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    import_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    english_word: Mapped[str] = mapped_column(String(255), nullable=False)
    translation: Mapped[str] = mapped_column(String(255), nullable=False)
    part_of_speech: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cefr_level: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    example_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    example_ru: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    synonyms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON raw AI feedback
    status: Mapped[str] = mapped_column(String(50), default="VALID", nullable=False)

    import_session: Mapped["Import"] = relationship("Import", back_populates="words")


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str] = mapped_column(String(20), default="🏆", nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    user_achievements: Mapped[List["UserAchievement"]] = relationship(
        "UserAchievement", back_populates="achievement", cascade="all, delete-orphan"
    )


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    achievement_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    unlocked_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="user_achievements")
    achievement: Mapped["Achievement"] = relationship("Achievement", back_populates="user_achievements")

    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
    )


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), index=True, nullable=False)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

