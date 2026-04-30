from writer_api.models.voice import VoiceProfile

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
