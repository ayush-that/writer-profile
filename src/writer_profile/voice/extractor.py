from __future__ import annotations

import json
import re

from writer_profile.corpus.models import Platform, Post
from writer_profile.llm import LLMClient, LLMMessage
from writer_profile.voice.profile import (
    LexicalProfile,
    RhetoricalProfile,
    StructuralProfile,
    TonalProfile,
    VoiceProfile,
)
from writer_profile.voice.stats import compute_stats


class VoiceExtractionError(Exception):
    """Raised when voice profile extraction fails."""


_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)

_SYSTEM_TEMPLATE = """You are an expert voice analyst. Given statistical fingerprints AND sample posts from one author on one platform, produce a structured JSON voice profile.

GROUND YOUR ANALYSIS IN THE STATS. Do not invent traits the numbers contradict.

STATS:
{stats_block}

SAMPLE POSTS (representative of this author on {platform}):
{samples_block}

Return ONLY a JSON object with these exact top-level keys:
- lexical: {{recurring_phrases: [str], word_preferences: {{word: 1|0}}, jargon_level: "low"|"medium"|"high", notes: str}}
- structural: {{typical_opener_patterns: [str], typical_closer_patterns: [str], paragraph_shape: str, list_usage: str, question_usage: str}}
- rhetorical: {{uses_analogies: bool, uses_personal_anecdotes: bool, uses_data_points: bool, attribution_style: str, name_drop_rate: "rare"|"occasional"|"moderate"|"frequent"}}
- tonal: {{warmth: "warm"|"neutral"|"distant", humor: "none"|"dry"|"playful"|"sharp", conviction: "low"|"medium"|"high", disclosure: "rare"|"occasional"|"moderate"|"frequent", vulnerability: "rare"|"occasional"|"moderate"|"frequent"}}
- examples: [str]  (3-5 verbatim posts that most exemplify the voice)

No prose. No explanation. Just the JSON."""


def _strip_fence(raw: str) -> str:
    m = _FENCE_RE.search(raw)
    return m.group(1) if m else raw.strip()


def _stats_block(stats) -> str:
    return json.dumps(stats.model_dump(), indent=2, default=str)


def _samples_block(posts: list[Post], limit: int = 40) -> str:
    sorted_posts = sorted(posts, key=lambda p: len(p.text), reverse=True)[:limit]
    return "\n\n---\n\n".join(p.text for p in sorted_posts)


def build_voice_profile(
    *,
    author: str,
    platform: Platform,
    posts: list[Post],
    llm: LLMClient,
    model: str,
) -> VoiceProfile:
    stats = compute_stats(posts)
    system = _SYSTEM_TEMPLATE.format(
        stats_block=_stats_block(stats),
        platform=platform.value,
        samples_block=_samples_block(posts),
    )
    raw = llm.complete(
        model=model,
        system=system,
        messages=[LLMMessage(role="user", content="Produce the JSON voice profile now.")],
        max_tokens=2048,
        temperature=0.1,
    )
    try:
        data = json.loads(_strip_fence(raw))
    except json.JSONDecodeError as e:
        raise VoiceExtractionError(
            f"Failed to parse LLM response as JSON: {e}. Raw: {raw[:200]}"
        ) from e

    return VoiceProfile(
        author=author,
        platform=platform,
        stats=stats,
        lexical=LexicalProfile.model_validate(data["lexical"]),
        structural=StructuralProfile.model_validate(data["structural"]),
        rhetorical=RhetoricalProfile.model_validate(data["rhetorical"]),
        tonal=TonalProfile.model_validate(data["tonal"]),
        examples=list(data.get("examples", [])),
    )
