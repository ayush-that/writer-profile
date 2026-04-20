from datetime import datetime, UTC

from writer_profile.corpus.models import Platform, Post
from writer_profile.voice.stats import compute_stats


def _p(pid: str, text: str) -> Post:
    return Post(
        id=pid, author="ali", platform=Platform.TWITTER,
        text=text, created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )


def test_compute_stats_basic_shape():
    posts = [
        _p("1", "AI is eating software. Again."),
        _p("2", "Open source wins. Always did. Always will."),
        _p("3", "Spark 4 ships vectorized execution today! 🚀"),
    ]
    s = compute_stats(posts)

    assert s.post_count == 3
    assert 3.0 <= s.avg_words_per_sentence <= 6.0
    assert 0.0 <= s.emoji_rate <= 1.0
    assert 0.0 <= s.hashtag_rate <= 1.0
    assert s.emoji_rate > 0.0  # one of the posts has an emoji
    assert len(s.top_openers) > 0
    assert len(s.top_closers) > 0
    assert len(s.length_chars_p25_p50_p75) == 3


def test_compute_stats_empty_corpus_errors():
    import pytest
    with pytest.raises(ValueError):
        compute_stats([])


def test_compute_stats_detects_hashtag_rate():
    posts = [
        _p("1", "launching today #databricks #ai"),
        _p("2", "no hashtags here"),
    ]
    s = compute_stats(posts)
    assert s.hashtag_rate == 0.5
