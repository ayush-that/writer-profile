from __future__ import annotations

import json
import re

from writer_profile.corpus.models import Post, PostMetadata
from writer_profile.llm import LLMClient, LLMMessage

_EXTRACT_SYSTEM = """You classify a single social post into structured metadata.

Return ONLY a JSON object with these exact keys:
- topics: array of 1-4 lowercase noun phrases (each 1-3 words)
- tone: one of "observational" | "contrarian" | "technical" | "story" | "promotional" | "question"
- length_bucket: one of "short" | "medium" | "long"
  - short: under 140 chars
  - medium: 140-500 chars
  - long: over 500 chars
- language: ISO 639-1 code (e.g. "en")

No prose. No explanation. Just the JSON object."""

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _strip_json_fence(raw: str) -> str:
    match = _FENCE_RE.search(raw)
    return match.group(1) if match else raw.strip()


def extract_metadata(post: Post, *, llm: LLMClient, model: str) -> PostMetadata:
    prompt = f"PLATFORM: {post.platform.value}\n\nPOST:\n{post.text}"
    raw = llm.complete(
        model=model,
        system=_EXTRACT_SYSTEM,
        messages=[LLMMessage(role="user", content=prompt)],
        max_tokens=256,
        temperature=0.0,
    )
    data = json.loads(_strip_json_fence(raw))
    return PostMetadata.model_validate(data)
