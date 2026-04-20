from __future__ import annotations

from writer_profile.corpus.models import Idea
from writer_profile.generation.prompts import build_generator_prompt
from writer_profile.llm import LLMClient, LLMMessage
from writer_profile.platforms.base import Constraint
from writer_profile.retrieval.store import ExemplarHit
from writer_profile.virality.hooks import Hook
from writer_profile.voice.profile import VoiceProfile


def unwrap(raw: str) -> str:
    text = raw.strip()
    if len(text) >= 2 and text[0] in {'"', "'"} and text[-1] == text[0]:
        text = text[1:-1].strip()
    return text


def generate_draft(
    *,
    profile: VoiceProfile,
    idea: Idea,
    exemplars: list[ExemplarHit],
    constraint: Constraint,
    hooks: list[Hook],
    llm: LLMClient,
    model: str,
    virality_strength: float = 0.15,
    temperature: float = 0.8,
) -> str:
    system, user = build_generator_prompt(
        profile=profile,
        idea=idea,
        exemplars=exemplars,
        constraint=constraint,
        hooks=hooks,
        virality_strength=virality_strength,
    )
    raw = llm.complete(
        model=model,
        system=system,
        messages=[LLMMessage(role="user", content=user)],
        max_tokens=1024,
        temperature=temperature,
    )
    return unwrap(raw)
