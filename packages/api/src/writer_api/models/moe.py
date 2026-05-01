from __future__ import annotations

from pydantic import BaseModel, Field

from writer_api.models.voice import Platform


class Candidate(BaseModel):
    text: str
    model: str
    latency_ms: int
    input_tokens: int = 0
    output_tokens: int = 0


class JudgeScore(BaseModel):
    judge_model: str
    candidate_index: int
    voice_match: float = Field(ge=0.0, le=1.0)
    virality: float = Field(ge=0.0, le=1.0)
    authenticity: float = Field(ge=0.0, le=1.0)
    overall: float = Field(ge=0.0, le=1.0)
    rationale: str = ""


class RetrievedContextSummary(BaseModel):
    own_post_count: int = 0
    web_post_count: int = 0
    own_post_authors: list[str] = Field(default_factory=list)


class MoEResponse(BaseModel):
    winner: Candidate
    candidates: list[Candidate]
    scores: list[JudgeScore]
    context: RetrievedContextSummary
    author: str
    platform: Platform
