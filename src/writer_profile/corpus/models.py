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
