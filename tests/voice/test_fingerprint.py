from datetime import UTC, datetime

import pytest

from writer_profile.corpus.models import Platform, Post
from writer_profile.voice.fingerprint import StyleFingerprint, compute_fingerprint

_DT = datetime(2024, 1, 1, tzinfo=UTC)


def _posts() -> list[Post]:
    return [
        Post(
            id="1",
            text="Hello world! This is a test.",
            platform=Platform.TWITTER,
            created_at=_DT,
            author="ali",
        ),
        Post(
            id="2",
            text="Another post here. Testing more.",
            platform=Platform.TWITTER,
            created_at=_DT,
            author="ali",
        ),
        Post(id="3", text="Short one.", platform=Platform.TWITTER, created_at=_DT, author="ali"),
    ]


def test_compute_fingerprint_returns_style_fingerprint():
    posts = _posts()
    fp = compute_fingerprint(posts)
    assert isinstance(fp, StyleFingerprint)
    assert fp.avg_word_length > 0
    assert 0 <= fp.vocabulary_richness <= 1
    assert len(fp.punctuation_rates) > 0
    assert len(fp.char_trigram_top10) <= 10


def test_compute_fingerprint_empty_raises():
    with pytest.raises(ValueError, match="empty"):
        compute_fingerprint([])


def test_fingerprint_deviation_same_author_is_low():
    posts = _posts()
    fp1 = compute_fingerprint(posts[:2])
    fp2 = compute_fingerprint(posts[1:])
    deviation = fp1.deviation_from(fp2)
    assert deviation < 0.5
