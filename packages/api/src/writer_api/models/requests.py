from pydantic import BaseModel, Field

from writer_api.models.voice import Platform


class GenerateRequest(BaseModel):
    author: str
    platform: Platform
    topic: str
    angle: str = ""
    virality: float = Field(0.15, ge=0.0, le=1.0)
    word_limit: int | None = Field(None, ge=20, le=1000)


class RevoiceRequest(BaseModel):
    author: str
    platform: Platform
    edited_draft: str
