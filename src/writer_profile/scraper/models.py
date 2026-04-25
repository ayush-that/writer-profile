from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Platform = Literal["linkedin", "youtube", "news"]
Source = Literal["exa", "youtube_transcript"]


class ScrapedPost(BaseModel):
    id: str
    author: str = Field(min_length=1)
    platform: Platform
    text: str = Field(min_length=1)
    created_at: datetime
    url: str = Field(min_length=1)
    source: Source


class ScrapeConfig(BaseModel):
    author_name: str = Field(min_length=1)
    linkedin_handle: str = Field(min_length=1)
    youtube_queries: list[str] = Field(default_factory=list)
    max_results_per_source: int = Field(default=50, ge=1, le=100)
