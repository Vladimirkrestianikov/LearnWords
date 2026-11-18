from typing import Optional, List
from pydantic import BaseModel, Field


class WordCardSchema(BaseModel):
    english_word: str = Field(description="English word or phrase")
    translation: str = Field(description="Russian translation")
    part_of_speech: str = Field(description="Part of speech, e.g. Noun, Verb, Adjective, Phrasal verb")
    cefr_level: str = Field(description="CEFR level: A1, A2, B1, B2, C1, or C2")
    topic: str = Field(description="Topic or semantic domain")
    example_en: str = Field(description="Natural example sentence in English containing the word")
    example_ru: str = Field(description="Accurate Russian translation of the example sentence")
    synonyms: List[str] = Field(default_factory=list, description="Common synonyms in English")
    notes: Optional[str] = Field(default=None, description="Usage note or nuance if helpful")


class GeneratedWordBatch(BaseModel):
    words: List[WordCardSchema] = Field(description="List of educational word cards")

