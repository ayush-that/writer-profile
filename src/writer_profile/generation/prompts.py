from __future__ import annotations

from writer_profile.corpus.models import Idea, Platform
from writer_profile.platforms.base import Constraint
from writer_profile.retrieval.store import ExemplarHit
from writer_profile.virality.hooks import Hook, HookLibrary
from writer_profile.voice.profile import VoiceProfile


def _format_exemplars(exemplars: list[ExemplarHit]) -> str:
    if not exemplars:
        return "(no retrieved exemplars — rely on profile + canonical examples)"
    blocks = []
    for i, h in enumerate(exemplars, start=1):
        blocks.append(
            f"EXAMPLE {i} (tone={h.metadata.tone.value}, "
            f"length={h.metadata.length_bucket}):\n{h.post.text}"
        )
    return "\n\n".join(blocks)


def _format_profile(profile: VoiceProfile) -> str:
    s = profile.stats
    lex = profile.lexical
    struct = profile.structural
    rhet = profile.rhetorical
    tone = profile.tonal

    return (
        f"AUTHOR: {profile.author} on {profile.platform.value}\n\n"
        "STATISTICAL FINGERPRINT:\n"
        f"- sentence length: avg {s.avg_words_per_sentence:.1f} words "
        f"(p25/p50/p75 = {s.sentence_length_p25_p50_p75[0]:.0f}/"
        f"{s.sentence_length_p25_p50_p75[1]:.0f}/"
        f"{s.sentence_length_p25_p50_p75[2]:.0f})\n"
        f"- post length chars p25/p50/p75: {s.length_chars_p25_p50_p75[0]:.0f}/"
        f"{s.length_chars_p25_p50_p75[1]:.0f}/"
        f"{s.length_chars_p25_p50_p75[2]:.0f}\n"
        f"- emoji usage: {s.emoji_rate*100:.0f}% of posts\n"
        f"- hashtag usage: {s.hashtag_rate*100:.0f}% of posts "
        f"(avg {s.avg_hashtags_per_post:.2f} per post)\n"
        f"- asks questions: {s.question_rate*100:.0f}% of posts\n"
        f"- mentions others: {s.mention_rate*100:.0f}% of posts\n"
        f"- typical openers (lowercased): {', '.join(s.top_openers[:5])}\n"
        f"- typical closers (lowercased): {', '.join(s.top_closers[:5])}\n\n"
        "LEXICAL:\n"
        f"- recurring phrases: {', '.join(lex.recurring_phrases[:8])}\n"
        f"- jargon level: {lex.jargon_level}\n"
        f"- notes: {lex.notes}\n\n"
        "STRUCTURAL:\n"
        f"- openers: {', '.join(struct.typical_opener_patterns)}\n"
        f"- closers: {', '.join(struct.typical_closer_patterns)}\n"
        f"- paragraph shape: {struct.paragraph_shape}\n"
        f"- list usage: {struct.list_usage}\n"
        f"- question usage: {struct.question_usage}\n\n"
        "RHETORICAL:\n"
        f"- analogies: {rhet.uses_analogies}, anecdotes: {rhet.uses_personal_anecdotes}, "
        f"data points: {rhet.uses_data_points}\n"
        f"- attribution: {rhet.attribution_style}\n"
        f"- name drops: {rhet.name_drop_rate}\n\n"
        "TONAL:\n"
        f"- warmth: {tone.warmth} / humor: {tone.humor} / "
        f"conviction: {tone.conviction} / disclosure: {tone.disclosure} / "
        f"vulnerability: {tone.vulnerability}\n\n"
        "CANONICAL EXAMPLES (most representative of this voice):\n"
        + "\n\n".join(f"- {e}" for e in profile.examples[:5])
    )


def build_generator_prompt(
    *,
    profile: VoiceProfile,
    idea: Idea,
    exemplars: list[ExemplarHit],
    constraint: Constraint,
    hooks: list[Hook],
    virality_strength: float = 0.15,
) -> tuple[str, str]:
    hook_block = HookLibrary.render_injection(hooks, virality_strength=virality_strength)

    system = (
        f"You write {profile.platform.value} posts in the EXACT voice of {profile.author}. "
        "Mimic cadence, sentence length, punctuation, and word choice. "
        "Do not invent a new voice. Do not sound like a corporate announcement.\n\n"
        f"{_format_profile(profile)}\n\n"
        f"RETRIEVED AUTHOR EXAMPLES (study these):\n{_format_exemplars(exemplars)}\n\n"
        f"PLATFORM RULES ({profile.platform.value}):\n{constraint.describe_rules()}\n\n"
        f"{hook_block}\n\n"
        "Output ONLY the post text. No preamble, no quotes, no explanation."
    )
    user = f"Write one post based on this brief.\n\n{idea.render()}"
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


def build_revoice_prompt(
    *,
    profile: VoiceProfile,
    edited_draft: str,
    constraint: Constraint,
) -> tuple[str, str]:
    system = (
        f"A human editor has structured a {profile.platform.value} post for {profile.author}. "
        "Your ONLY job is to refine the voice — word choice, cadence, phrasing — to match this "
        "author's profile. You MUST preserve:\n"
        "- paragraph count and relative order\n"
        "- key noun phrases / entities the editor included\n"
        "- the editor's structural intent (list vs prose, question vs statement, hook location)\n\n"
        "You MUST NOT:\n"
        "- reorder paragraphs\n"
        "- add or remove points\n"
        "- change the narrative arc\n\n"
        f"{_format_profile(profile)}\n\n"
        f"PLATFORM RULES ({profile.platform.value}):\n{constraint.describe_rules()}\n\n"
        "Output ONLY the revoiced post. No preamble."
    )
    user = f"EDITED DRAFT TO REVOICE:\n{edited_draft}\n\nRevoiced post:"
    return system, user
