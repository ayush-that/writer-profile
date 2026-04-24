from __future__ import annotations

from pydantic import BaseModel, Field


class TraitVector(BaseModel):
    """6-dimensional personality trait vector for voice characterization."""

    warmth: float = Field(default=0.5, ge=0.0, le=1.0, description="cold (0) to warm (1)")
    humor: float = Field(default=0.5, ge=0.0, le=1.0, description="serious (0) to playful (1)")
    formality: float = Field(default=0.5, ge=0.0, le=1.0, description="casual (0) to formal (1)")
    energy: float = Field(default=0.5, ge=0.0, le=1.0, description="calm (0) to energetic (1)")
    conviction: float = Field(default=0.5, ge=0.0, le=1.0, description="tentative (0) to assertive (1)")
    disclosure: float = Field(default=0.5, ge=0.0, le=1.0, description="guarded (0) to open (1)")

    def blend(self, other: TraitVector, alpha: float = 0.5) -> TraitVector:
        return TraitVector(
            warmth=self.warmth * (1 - alpha) + other.warmth * alpha,
            humor=self.humor * (1 - alpha) + other.humor * alpha,
            formality=self.formality * (1 - alpha) + other.formality * alpha,
            energy=self.energy * (1 - alpha) + other.energy * alpha,
            conviction=self.conviction * (1 - alpha) + other.conviction * alpha,
            disclosure=self.disclosure * (1 - alpha) + other.disclosure * alpha,
        )

    def to_prompt_description(self) -> str:
        parts = []

        if self.warmth >= 0.7:
            parts.append("warm and approachable")
        elif self.warmth <= 0.3:
            parts.append("professional and measured")

        if self.humor >= 0.7:
            parts.append("playful with occasional wit")
        elif self.humor <= 0.3:
            parts.append("serious and direct")

        if self.formality >= 0.7:
            parts.append("formal in register")
        elif self.formality <= 0.3:
            parts.append("conversational and casual")

        if self.energy >= 0.7:
            parts.append("energetic and enthusiastic")
        elif self.energy <= 0.3:
            parts.append("calm and deliberate")

        if self.conviction >= 0.7:
            parts.append("confident and assertive")
        elif self.conviction <= 0.3:
            parts.append("thoughtful and nuanced")

        if self.disclosure >= 0.7:
            parts.append("openly personal")
        elif self.disclosure <= 0.3:
            parts.append("professionally reserved")

        if not parts:
            return "balanced and adaptable in tone"
        return ", ".join(parts)
