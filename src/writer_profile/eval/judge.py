from __future__ import annotations

import json
import re

from pydantic import BaseModel

from writer_profile.corpus.models import Platform, Post
from writer_profile.llm import LLMClient, LLMMessage

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)


class JudgeScore(BaseModel):
    voice_fidelity: int
    voice_reasoning: str
    naturalness: int
    naturalness_reasoning: str
    ai_tics: list[str]


def _strip_fence(raw: str) -> str:
    m = _FENCE_RE.search(raw)
    return m.group(1) if m else raw.strip()


_SYSTEM = """You are an expert judge of voice fidelity for social media posts.

You are given:
- an AUTHOR whose voice we are attempting to reproduce
- REFERENCE posts from that author on {platform}
- ONE CANDIDATE post allegedly in that author's voice

Score two axes on a 1-10 integer scale:
- voice_fidelity: does the candidate sound like the same writer as the references? 10 = indistinguishable, 1 = obviously a different person.
- naturalness: does the candidate read like a real human? 10 = fully natural, 1 = obvious AI output.

Also flag "ai_tics": specific words, phrases, or structural moves in the candidate that read as AI-generated (e.g. "Furthermore,", em-dash overuse, balanced three-part lists, empty intensifiers).

REFERENCE POSTS (author's real {platform} output):
{references_block}

Return ONLY a JSON object:
{{"voice_fidelity": int, "voice_reasoning": str, "naturalness": int, "naturalness_reasoning": str, "ai_tics": [str]}}

No prose. No explanation. Just the JSON."""  # noqa: E501


def score_post(
    *,
    author: str,
    platform: Platform,
    candidate: str,
    references: list[Post],
    llm: LLMClient,
    model: str,
) -> JudgeScore:
    refs = "\n\n---\n\n".join(p.text for p in references)
    system = _SYSTEM.format(platform=platform.value, references_block=refs)

    raw = llm.complete(
        model=model,
        system=system,
        messages=[
            LLMMessage(role="user", content=f"CANDIDATE POST by '{author}':\n\n{candidate}")
        ],
        max_tokens=512,
        temperature=0.0,
    )
    data = json.loads(_strip_fence(raw))
    return JudgeScore.model_validate(data)
