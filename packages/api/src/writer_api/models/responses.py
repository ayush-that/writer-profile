from pydantic import BaseModel, Field

from writer_api.models.voice import Platform, VoiceProfile


class GenerateResponse(BaseModel):
    """Response containing generated content."""

    text: str = Field(..., description="Generated post text")
    author: str = Field(..., description="CEO identifier used")
    platform: Platform = Field(..., description="Target platform")
    validation_ok: bool = Field(True, description="Whether validation passed")
    validation_issues: list[str] = Field(default_factory=list)
    sources_used: int = Field(0, description="Number of reference sources used")


class ProfileResponse(BaseModel):
    """Response containing a voice profile."""

    profile: VoiceProfile = Field(..., description="The voice profile")
    post_count: int = Field(0, description="Number of example posts in profile")


class ProfileListResponse(BaseModel):
    """Response containing a list of profiles."""

    profiles: list[dict[str, str]] = Field(..., description="List of profile summaries")
