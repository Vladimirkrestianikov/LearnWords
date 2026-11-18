from typing import Optional, List
from pydantic import BaseModel, Field


class AnswerEvaluation(BaseModel):
    is_correct: bool = Field(description="True if student answer conveys the correct meaning and grammar, even if synonymous or phrased differently")
    quality_score: int = Field(description="Quality score from 0 (total blackout/wrong) to 5 (flawless): 5=perfect, 4=minor typo/good, 3=hesitant but correct, 2=almost right, 1=wrong but familiar, 0=completely wrong")
    correct_answer: str = Field(description="The primary recommended correct answer")
    explanation: str = Field(description="Clear Russian explanation of why it is correct or what mistake was made")
    acceptable_alternatives: List[str] = Field(default_factory=list, description="Other acceptable synonyms or translations")
    memory_tip: str = Field(description="Short, memorable mnemonic or tip for remembering this word or rule")


class StagedWordItem(BaseModel):
    english_word: str = Field(description="Normalized English word or phrasal verb")
    translation: str = Field(description="Accurate Russian translation")
    part_of_speech: Optional[str] = Field(default=None, description="Part of speech: Noun, Verb, Adjective, etc.")
    cefr_level: Optional[str] = Field(default=None, description="Estimated CEFR level: A1, A2, B1, B2, C1, C2")
    topic: Optional[str] = Field(default=None, description="Thematic topic")
    example_en: Optional[str] = Field(default=None, description="Example sentence in English")
    example_ru: Optional[str] = Field(default=None, description="Translation of example sentence")
    synonyms: List[str] = Field(default_factory=list, description="Synonyms in English")
    notes: Optional[str] = Field(default=None, description="Notes on nuance or corrected typos")
    is_ambiguous: bool = Field(default=False, description="True if translation is ambiguous or needs clarification")


class StagedImportAnalysis(BaseModel):
    words: List[StagedWordItem] = Field(description="Extracted and enriched list of vocabulary words")
    total_recognized: int = Field(description="Total number of successfully parsed word items")
    summary: str = Field(description="Brief summary of import findings in Russian")


class GeneratedQuizQuestion(BaseModel):
    question_type: str = Field(description="Question type code: CHOICE, FILL_BLANK, MAKE_SENTENCE, SENTENCE_TRANSLATION, CONTEXT_DEFINITION")
    target_word: str = Field(description="The English word being tested")
    prompt: str = Field(description="Instruction or prompt shown to user in Russian or English")
    context_sentence: Optional[str] = Field(default=None, description="Sentence with blank or highlighted word, if applicable")
    options: List[str] = Field(default_factory=list, description="4 options (A, B, C, D) for CHOICE questions")
    correct_answer: str = Field(description="Correct choice letter or exact word/translation")
    hint: Optional[str] = Field(default=None, description="Optional hint for user")

