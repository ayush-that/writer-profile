from pydantic import BaseModel, Field

from writer_api.models.voice import Platform, VoiceProfile


class Source(BaseModel):
    url: str
    title: str = ""
    source_type: str = ""
    snippet: str = ""


class GenerateResponse(BaseModel):
    text: str
    author: str
    platform: Platform
    validation_ok: bool = True
    validation_issues: list[str] = Field(default_factory=list)
    sources_used: int = 0
    sources: list[Source] = Field(default_factory=list)


class ProfileResponse(BaseModel):
    profile: VoiceProfile
    post_count: int = 0


class ProfileListResponse(BaseModel):
    profiles: list[dict[str, str]]
