from __future__ import annotations

from writer_profile.corpus.models import Platform
from writer_profile.platforms.base import Constraint
from writer_profile.retrieval.store import ExemplarHit


def _format_exemplars(exemplars: list[ExemplarHit]) -> str:
    if not exemplars:
        return "(none available)"
    blocks = []
    for i, h in enumerate(exemplars, start=1):
        blocks.append(
            f"EXAMPLE {i} (tone={h.metadata.tone.value}, "
            f"length={h.metadata.length_bucket}):\n{h.post.text}"
        )
    return "\n\n".join(blocks)


def build_generator_prompt(
    *,
    topic: str,
    platform: Platform,
    exemplars: list[ExemplarHit],
    constraint: Constraint,
) -> tuple[str, str]:
    system = (
        f"You write {platform.value} posts in the exact voice of a specific author. "
        "Mimic their cadence, sentence length, punctuation, and word choice. "
        "Do not invent a new voice.\n\n"
        f"AUTHOR VOICE EXAMPLES (study these carefully):\n\n{_format_exemplars(exemplars)}\n\n"
        f"PLATFORM RULES ({platform.value}):\n{constraint.describe_rules()}\n\n"
        "Output ONLY the post text. No preamble, no quotes, no explanation."
    )
    user = f"Write one post on this topic: {topic}"
    return system, user


def build_critic_prompt(
    *,
    draft: str,
    platform: Platform,
    constraint: Constraint,
) -> tuple[str, str]:
    system = (
        "You are a terse editor critiquing one draft post. "
        "You do not rewrite. You give at most 3 concrete, actionable bullet points "
        "on what to improve — focus on voice fidelity, hook strength, and whether "
        "the post earns its length. If the draft is already strong, reply exactly: OK.\n\n"
        f"PLATFORM RULES ({platform.value}):\n{constraint.describe_rules()}"
    )
    user = f"DRAFT:\n{draft}\n\nYour critique:"
    return system, user


def build_refine_prompt(
    *,
    draft: str,
    platform: Platform,
    constraint: Constraint,
    critic_feedback: str,
    validator_issues: list[str],
) -> tuple[str, str]:
    validator_block = (
        "\n".join(f"- {i}" for i in validator_issues) if validator_issues else "(validator passed)"
    )
    system = (
        f"You revise a {platform.value} post based on explicit feedback. "
        "Keep the author's voice. Output ONLY the revised post text — no preamble, "
        "no quotes, no explanation.\n\n"
        f"PLATFORM RULES ({platform.value}):\n{constraint.describe_rules()}"
    )
    user = (
        f"ORIGINAL DRAFT:\n{draft}\n\n"
        f"CRITIC FEEDBACK:\n{critic_feedback}\n\n"
        f"HARD VALIDATOR ISSUES (must fix):\n{validator_block}\n\n"
        "Revised post:"
    )
    return system, user
