from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Platform(StrEnum):
    TWITTER = "twitter"
    LINKEDIN = "linkedin"


class Tone(StrEnum):
    OBSERVATIONAL = "observational"
    CONTRARIAN = "contrarian"
    TECHNICAL = "technical"
    STORY = "story"
    PROMOTIONAL = "promotional"
    QUESTION = "question"


LengthBucket = Literal["short", "medium", "long"]


class Post(BaseModel):
    id: str
    author: str = Field(min_length=1)
    platform: Platform
    text: str = Field(min_length=1)
    created_at: datetime
    engagement: dict[str, int] | None = None


class PostMetadata(BaseModel):
    topics: list[str] = Field(min_length=1)
    tone: Tone
    length_bucket: LengthBucket
    language: str = Field(min_length=2, max_length=5)


class AnnotatedPost(BaseModel):
    post: Post
    metadata: PostMetadata


class Idea(BaseModel):
    topic: str = Field(min_length=1)
    angle: str = ""
    constraints: list[str] = Field(default_factory=list)

    def render(self) -> str:
        parts = [f"TOPIC: {self.topic}"]
        if self.angle:
            parts.append(f"ANGLE: {self.angle}")
        if self.constraints:
            parts.append("MUST INCLUDE:\n" + "\n".join(f"- {c}" for c in self.constraints))
        return "\n\n".join(parts)
