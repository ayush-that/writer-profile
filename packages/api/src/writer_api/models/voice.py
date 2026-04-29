from enum import StrEnum

from pydantic import BaseModel, Field


class Platform(StrEnum):
    twitter = "twitter"
    linkedin = "linkedin"


class LexicalPatterns(BaseModel):
    vocabulary_level: str = "professional"
    recurring_phrases: list[str] = Field(default_factory=list)
    word_preferences: dict[str, str] = Field(default_factory=dict)
    jargon_usage: str = "moderate"
    technicality_level: str = "accessible"


class StructuralPatterns(BaseModel):
    avg_sentence_length: float = 15.0
    paragraph_style: str = "short"
    opening_patterns: list[str] = Field(default_factory=list)
    closing_patterns: list[str] = Field(default_factory=list)
    uses_lists: bool = False
    uses_questions: bool = False


class TonalPatterns(BaseModel):
    warmth_level: str = "moderate"
    humor_usage: str = "rare"
    personal_disclosure: str = "minimal"
    conviction_style: str = "confident"


class VoiceProfile(BaseModel):
    author: str
    platform: Platform
    lexical: LexicalPatterns = Field(default_factory=LexicalPatterns)
    structural: StructuralPatterns = Field(default_factory=StructuralPatterns)
    tonal: TonalPatterns = Field(default_factory=TonalPatterns)
    example_posts: list[str] = Field(default_factory=list)
