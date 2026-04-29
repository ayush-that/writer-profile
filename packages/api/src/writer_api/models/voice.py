from enum import StrEnum

from pydantic import BaseModel, Field


class Platform(StrEnum):
    """Supported social media platforms."""

    twitter = "twitter"
    linkedin = "linkedin"


class LexicalPatterns(BaseModel):
    """Lexical patterns extracted from a writer's content."""

    vocabulary_level: str = Field(default="professional")
    recurring_phrases: list[str] = Field(default_factory=list)
    word_preferences: dict[str, str] = Field(default_factory=dict)
    jargon_usage: str = Field(default="moderate")
    technicality_level: str = Field(default="accessible")


class StructuralPatterns(BaseModel):
    """Structural patterns in a writer's content."""

    avg_sentence_length: float = Field(default=15.0)
    paragraph_style: str = Field(default="short")
    opening_patterns: list[str] = Field(default_factory=list)
    closing_patterns: list[str] = Field(default_factory=list)
    uses_lists: bool = Field(default=False)
    uses_questions: bool = Field(default=False)


class TonalPatterns(BaseModel):
    """Tonal characteristics of a writer's voice."""

    warmth_level: str = Field(default="moderate")
    humor_usage: str = Field(default="rare")
    personal_disclosure: str = Field(default="minimal")
    conviction_style: str = Field(default="confident")


class VoiceProfile(BaseModel):
    """Complete voice profile for a writer."""

    author: str = Field(..., description="Author identifier")
    platform: Platform = Field(..., description="Target platform")
    lexical: LexicalPatterns = Field(default_factory=LexicalPatterns)
    structural: StructuralPatterns = Field(default_factory=StructuralPatterns)
    tonal: TonalPatterns = Field(default_factory=TonalPatterns)
    example_posts: list[str] = Field(default_factory=list)
