from pydantic import BaseModel, Field

from writer_api.models.voice import Platform


class GenerateRequest(BaseModel):
    """Request to generate new content in a CEO's voice."""

    author: str = Field(..., description="CEO identifier (e.g., 'ali_ghodsi')")
    platform: Platform = Field(..., description="Target platform")
    topic: str = Field(..., description="Topic or subject of the post")
    angle: str = Field("", description="Narrative direction or angle")
    virality: float = Field(0.15, ge=0.0, le=1.0, description="Virality hook strength")


class RevoiceRequest(BaseModel):
    """Request to re-voice an edited draft."""

    author: str = Field(..., description="CEO identifier")
    platform: Platform = Field(..., description="Target platform")
    edited_draft: str = Field(..., description="Human-edited draft to re-voice")
