from __future__ import annotations

from typing import TYPE_CHECKING

from writer_api.models.voice import VoiceProfile

if TYPE_CHECKING:
    from writer_api.services.hybrid_retriever import HybridBundle

GENERATOR_SYSTEM = """You are a ghostwriter who perfectly mimics a CEO's authentic voice for social media.

Your task: Generate a {platform} post that sounds exactly like {author} wrote it.

## Voice Profile
{voice_profile}

## Reference Posts (from their actual content)
{reference_posts}

## Guidelines
- Match their exact vocabulary, sentence patterns, and tone
- Use their typical opening and closing styles
- Match their formatting habits (line breaks, lists, questions)
- Keep the authentic feel - never sound corporate or generic
- For Twitter/X: stay within character limits, thread if needed
- For LinkedIn: match their typical post length and structure

## Virality Enhancement ({virality_pct}% influence)
Subtly incorporate high-performing structural patterns:
- Strong hook in first line
- Clear narrative arc
- Memorable closing

Output ONLY the post text, nothing else."""


REVOICE_SYSTEM = """You are a voice refinement expert. Your task is to take a human-edited draft and apply {author}'s authentic voice to it.

## Voice Profile
{voice_profile}

## Key Constraint
The human made structural choices intentionally. Preserve:
- Their paragraph organization
- Their key points and order
- Any specific phrasing they emphasized

Only refine the VOICE:
- Vocabulary choices
- Sentence rhythm
- Tonal register
- Opening/closing style

Output ONLY the refined post, nothing else."""


def build_generator_prompt(
    profile: VoiceProfile,
    topic: str,
    angle: str,
    references: list[dict],
    virality: float,
    word_limit: int | None = None,
) -> tuple[str, str]:
    voice_summary = f"""
Author: {profile.author}
Platform: {profile.platform.value}
Lexical: {profile.lexical.vocabulary_level} vocabulary, technicality: {profile.lexical.technicality_level}
Recurring phrases: {", ".join(profile.lexical.recurring_phrases[:5])}
Structural: {profile.structural.paragraph_style}, avg sentence length: {profile.structural.avg_sentence_length:.0f} words
Opens with: {", ".join(profile.structural.opening_patterns[:3])}
Closes with: {", ".join(profile.structural.closing_patterns[:3])}
Tone: {profile.tonal.warmth_level} warmth, {profile.tonal.humor_usage} humor, {profile.tonal.conviction_style} conviction
"""

    if references:
        ref_posts = "\n---\n".join(
            [
                f"[{r.get('source_type', 'post')}] {r.get('text', '')[:500]}..."
                if len(r.get("text", "")) > 500
                else f"[{r.get('source_type', 'post')}] {r.get('text', '')}"
                for r in references[:5]
            ]
        )
    else:
        ref_posts = "\n---\n".join(profile.example_posts[:3])

    system = GENERATOR_SYSTEM.format(
        platform=profile.platform.value,
        author=profile.author,
        voice_profile=voice_summary,
        reference_posts=ref_posts,
        virality_pct=int(virality * 100),
    )

    if word_limit:
        system = system.replace(
            "## Virality Enhancement",
            f"## Word Limit\nTARGET LENGTH: Approximately {word_limit} words. Stay close to this target.\n\n## Virality Enhancement"
        )

    user = f"""Generate a {profile.platform.value} post for {profile.author}.

Topic: {topic}
Angle: {angle if angle else "Choose the best angle for engagement"}

Write the post now:"""

    return system, user


def build_revoice_prompt(profile: VoiceProfile, edited_draft: str) -> tuple[str, str]:
    voice_summary = f"""
Author: {profile.author}
Platform: {profile.platform.value}
Tone: {profile.tonal.warmth_level} warmth, {profile.tonal.conviction_style} conviction
Style: {profile.structural.paragraph_style}
"""

    system = REVOICE_SYSTEM.format(
        author=profile.author,
        voice_profile=voice_summary,
    )

    user = f"Re-voice this draft:\n\n{edited_draft}"

    return system, user


GENERATOR_HYBRID_SYSTEM = """You are a ghostwriter who perfectly mimics a CEO's authentic voice for social media.

Your task: Generate a {platform} post that sounds exactly like {author} wrote it.

## Voice Profile
{voice_profile}

## REFERENCE - author's own past posts (match this voice)
{own_posts}

## CONTEXT - recent web mentions of this topic (use for facts/current events, NOT voice)
{web_posts}

## Guidelines
- The REFERENCE section is the source of voice truth. Match its vocabulary, sentence patterns, tone.
- The CONTEXT section is for factual grounding only. Do NOT copy its phrasing or style.
- Use {author}'s typical opening and closing styles
- Match their formatting habits (line breaks, lists, questions)
- Keep the authentic feel - never sound corporate or generic
- For Twitter/X: stay within character limits, thread if needed
- For LinkedIn: match their typical post length and structure

## Virality Enhancement ({virality_pct}% influence)
Subtly incorporate high-performing structural patterns:
- Strong hook in first line
- Clear narrative arc
- Memorable closing

Output ONLY the post text, nothing else."""


def _truncate(text: str, limit: int = 500) -> str:
    text = text or ""
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def _format_own_posts(bundle: HybridBundle, profile: VoiceProfile) -> str:
    if bundle.own_posts:
        return "\n---\n".join(_truncate(item.text) for item in bundle.own_posts)
    if profile.example_posts:
        return "\n---\n".join(_truncate(p) for p in profile.example_posts[:3])
    return "(no reference posts available)"


def _format_web_posts(bundle: HybridBundle) -> str:
    if not bundle.web_posts:
        return "(no recent web context available)"
    return "\n---\n".join(_truncate(item.text) for item in bundle.web_posts)


def build_generator_prompt_hybrid(
    profile: VoiceProfile,
    topic: str,
    angle: str,
    bundle: HybridBundle,
    virality: float,
    word_limit: int | None = None,
) -> tuple[str, str]:
    voice_summary = f"""
Author: {profile.author}
Platform: {profile.platform.value}
Lexical: {profile.lexical.vocabulary_level} vocabulary, technicality: {profile.lexical.technicality_level}
Recurring phrases: {", ".join(profile.lexical.recurring_phrases[:5])}
Structural: {profile.structural.paragraph_style}, avg sentence length: {profile.structural.avg_sentence_length:.0f} words
Opens with: {", ".join(profile.structural.opening_patterns[:3])}
Closes with: {", ".join(profile.structural.closing_patterns[:3])}
Tone: {profile.tonal.warmth_level} warmth, {profile.tonal.humor_usage} humor, {profile.tonal.conviction_style} conviction
"""

    system = GENERATOR_HYBRID_SYSTEM.format(
        platform=profile.platform.value,
        author=profile.author,
        voice_profile=voice_summary,
        own_posts=_format_own_posts(bundle, profile),
        web_posts=_format_web_posts(bundle),
        virality_pct=int(virality * 100),
    )

    if word_limit:
        system = system.replace(
            "## Virality Enhancement",
            f"## Word Limit\nTARGET LENGTH: Approximately {word_limit} words. Stay close to this target.\n\n## Virality Enhancement",
        )

    user = f"""Generate a {profile.platform.value} post for {profile.author}.

Topic: {topic}
Angle: {angle if angle else "Choose the best angle for engagement"}

Write the post now:"""

    return system, user


JUDGE_SYSTEM = """You are a strict critic evaluating a ghostwritten {platform} post for {author}.

You will be shown:
1. A set of REFERENCE posts that {author} actually wrote (the voice anchor).
2. A CANDIDATE post written by an LLM trying to imitate {author}.

Score the candidate on three dimensions, each from 0.0 to 1.0:

- voice_match: How closely the candidate matches the REFERENCE author's voice (vocabulary, rhythm, tone, opening/closing patterns). 1.0 = indistinguishable from the reference. 0.0 = clearly a different writer.
- virality: Engagement potential on {platform}. Strong hook, clear payoff, shareable. 1.0 = high viral potential. 0.0 = forgettable.
- authenticity: Sounds like a real human, not LLM slop. 1.0 = feels human, specific, concrete. 0.0 = generic AI-flavored corporate-speak.

Return ONLY valid JSON, no markdown fences, no commentary, in this exact shape:

{{"voice_match": 0.0, "virality": 0.0, "authenticity": 0.0, "rationale": "one-sentence why"}}
"""


def build_judge_prompt(
    profile: VoiceProfile,
    candidate_text: str,
    bundle: HybridBundle,
    candidate_index: int,
) -> tuple[str, str]:
    system = JUDGE_SYSTEM.format(
        platform=profile.platform.value,
        author=profile.author,
    )

    references = _format_own_posts(bundle, profile)

    user = f"""## REFERENCE posts by {profile.author}
{references}

## CANDIDATE #{candidate_index}
{candidate_text}

Score the candidate now. Return ONLY the JSON object, nothing else."""

    return system, user
