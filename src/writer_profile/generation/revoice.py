from __future__ import annotations

from writer_profile.generation.generator import unwrap
from writer_profile.generation.prompts import build_revoice_prompt
from writer_profile.llm import LLMClient, LLMMessage
from writer_profile.platforms.base import Constraint
from writer_profile.voice.profile import VoiceProfile


def revoice(
    *,
    profile: VoiceProfile,
    edited_draft: str,
    constraint: Constraint,
    llm: LLMClient,
    model: str,
    temperature: float = 0.4,
) -> str:
    system, user = build_revoice_prompt(
        profile=profile, edited_draft=edited_draft, constraint=constraint
    )
    raw = llm.complete(
        model=model,
        system=system,
        messages=[LLMMessage(role="user", content=user)],
        max_tokens=1024,
        temperature=temperature,
    )
    return unwrap(raw)
