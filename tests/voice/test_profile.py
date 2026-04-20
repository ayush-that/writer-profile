import json
from pathlib import Path

from writer_profile.corpus.models import Platform
from writer_profile.voice.profile import (
    LexicalProfile,
    RhetoricalProfile,
    StructuralProfile,
    TonalProfile,
    VoiceProfile,
)
from writer_profile.voice.stats import VoiceStats


def _stats_stub() -> VoiceStats:
    return VoiceStats(
        post_count=100,
        avg_words_per_sentence=14.2,
        sentence_length_p25_p50_p75=(7.0, 12.0, 20.0),
        length_chars_p25_p50_p75=(90.0, 170.0, 260.0),
        emoji_rate=0.05,
        hashtag_rate=0.10,
        avg_hashtags_per_post=0.15,
        url_rate=0.22,
        question_rate=0.18,
        mention_rate=0.30,
        line_break_rate=0.12,
        top_openers=["at databricks we", "open source is"],
        top_closers=["what do you think?", "let me know"],
        top_bigrams=[("open source", 20)],
        top_trigrams=[("open source wins", 10)],
        thread_rate=0.08,
    )


def test_voice_profile_roundtrip(tmp_path: Path):
    vp = VoiceProfile(
        author="ali_ghodsi",
        platform=Platform.LINKEDIN,
        stats=_stats_stub(),
        lexical=LexicalProfile(
            recurring_phrases=["open source", "compound ai"],
            word_preferences={"team": 1, "folks": 0},
            jargon_level="medium",
            notes="light on jargon, heavy on conviction words",
        ),
        structural=StructuralProfile(
            typical_opener_patterns=["declarative one-liner", "contrarian hook"],
            typical_closer_patterns=["forward-looking statement"],
            paragraph_shape="3-5 short paragraphs with blank lines between",
            list_usage="rarely uses bullet lists",
            question_usage="occasional audience question at close",
        ),
        rhetorical=RhetoricalProfile(
            uses_analogies=True,
            uses_personal_anecdotes=True,
            uses_data_points=True,
            attribution_style="credits team + external contributors by name",
            name_drop_rate="moderate",
        ),
        tonal=TonalProfile(
            warmth="warm",
            humor="dry",
            conviction="high",
            disclosure="moderate",
            vulnerability="rare",
        ),
        examples=["open source wins. it always has.", "today we ship..."],
    )

    # roundtrip via JSON
    raw = vp.model_dump_json()
    restored = VoiceProfile.model_validate_json(raw)
    assert restored.author == "ali_ghodsi"
    assert restored.platform is Platform.LINKEDIN
    assert restored.stats.post_count == 100
    assert "open source" in restored.lexical.recurring_phrases
    assert restored.tonal.conviction == "high"

    # writable to disk and reloadable
    p = tmp_path / "profile.json"
    p.write_text(raw)
    reloaded = VoiceProfile.model_validate_json(p.read_text())
    assert reloaded == restored
