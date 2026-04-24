from pathlib import Path

import pytest

from writer_profile.corpus.models import Platform
from writer_profile.voice.profile import (
    LexicalProfile,
    RhetoricalProfile,
    StructuralProfile,
    TonalProfile,
    VoiceProfile,
)
from writer_profile.voice.stats import VoiceStats
from writer_profile.voice.store import VoiceProfileStore


def _profile(author: str, platform: Platform) -> VoiceProfile:
    return VoiceProfile(
        author=author,
        platform=platform,
        stats=VoiceStats(
            post_count=10,
            avg_words_per_sentence=12.0,
            sentence_length_p25_p50_p75=(6.0, 11.0, 18.0),
            length_chars_p25_p50_p75=(80.0, 150.0, 220.0),
            emoji_rate=0.1,
            hashtag_rate=0.0,
            avg_hashtags_per_post=0.0,
            url_rate=0.2,
            question_rate=0.1,
            mention_rate=0.3,
            line_break_rate=0.05,
            top_openers=["hi"],
            top_closers=["bye"],
            top_bigrams=[("hi there", 2)],
            top_trigrams=[],
            thread_rate=0.0,
        ),
        lexical=LexicalProfile(
            recurring_phrases=["x"], word_preferences={"a": 1}, jargon_level="low", notes=""
        ),
        structural=StructuralProfile(
            typical_opener_patterns=[],
            typical_closer_patterns=[],
            paragraph_shape="",
            list_usage="",
            question_usage="",
        ),
        rhetorical=RhetoricalProfile(
            uses_analogies=False,
            uses_personal_anecdotes=False,
            uses_data_points=False,
            attribution_style="",
            name_drop_rate="rare",
        ),
        tonal=TonalProfile(
            warmth="neutral",
            humor="none",
            conviction="low",
            disclosure="rare",
            vulnerability="rare",
        ),
        examples=["hi"],
    )


def test_store_save_and_load_roundtrip(tmp_path: Path):
    store = VoiceProfileStore(root=tmp_path)
    p = _profile("ali", Platform.TWITTER)
    store.save(p)

    out = store.load(author="ali", platform=Platform.TWITTER)
    assert out == p


def test_store_missing_profile_raises(tmp_path: Path):
    store = VoiceProfileStore(root=tmp_path)
    with pytest.raises(FileNotFoundError):
        store.load(author="nobody", platform=Platform.TWITTER)


def test_store_rejects_invalid_author_names(tmp_path: Path):
    store = VoiceProfileStore(root=tmp_path)

    invalid_names = ["../etc/passwd", "foo\x00bar", "a/b/c", "..\\windows"]
    for name in invalid_names:
        with pytest.raises(ValueError, match="Invalid author name"):
            store.save(_profile(name, Platform.TWITTER))


def test_store_list_profiles(tmp_path: Path):
    store = VoiceProfileStore(root=tmp_path)
    store.save(_profile("ali", Platform.TWITTER))
    store.save(_profile("ali", Platform.LINKEDIN))
    store.save(_profile("matei", Platform.TWITTER))

    entries = sorted(store.list_profiles())
    assert entries == [
        ("ali", Platform.LINKEDIN),
        ("ali", Platform.TWITTER),
        ("matei", Platform.TWITTER),
    ]
