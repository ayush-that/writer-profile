from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from writer_profile.corpus.models import Platform
from writer_profile.voice.stats import VoiceStats

JargonLevel = Literal["low", "medium", "high"]
Intensity = Literal["rare", "occasional", "moderate", "frequent"]
Register = Literal["warm", "neutral", "distant"]
HumorStyle = Literal["none", "dry", "playful", "sharp"]
ConvictionLevel = Literal["low", "medium", "high"]


class LexicalProfile(BaseModel):
    model_config = ConfigDict(frozen=True)
    recurring_phrases: list[str]
    word_preferences: dict[str, int]
    jargon_level: JargonLevel
    notes: str = ""


class StructuralProfile(BaseModel):
    model_config = ConfigDict(frozen=True)
    typical_opener_patterns: list[str]
    typical_closer_patterns: list[str]
    paragraph_shape: str
    list_usage: str
    question_usage: str


class RhetoricalProfile(BaseModel):
    model_config = ConfigDict(frozen=True)
    uses_analogies: bool
    uses_personal_anecdotes: bool
    uses_data_points: bool
    attribution_style: str
    name_drop_rate: Intensity


class TonalProfile(BaseModel):
    model_config = ConfigDict(frozen=True)
    warmth: Register
    humor: HumorStyle
    conviction: ConvictionLevel
    disclosure: Intensity
    vulnerability: Intensity


class VoiceProfile(BaseModel):
    author: str
    platform: Platform
    stats: VoiceStats
    lexical: LexicalProfile
    structural: StructuralProfile
    rhetorical: RhetoricalProfile
    tonal: TonalProfile
    examples: list[str]
