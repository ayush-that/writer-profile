from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from writer_profile.corpus.models import Platform, Post, PostMetadata, Tone


def test_post_requires_text_and_platform():
    post = Post(
        id="t1",
        platform=Platform.TWITTER,
        text="hello world",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    assert post.text == "hello world"
    assert post.platform is Platform.TWITTER


def test_post_rejects_empty_text():
    with pytest.raises(ValidationError):
        Post(
            id="t1",
            platform=Platform.TWITTER,
            text="",
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )


def test_post_metadata_bucket_length():
    meta = PostMetadata(
        topics=["ai", "tooling"],
        tone=Tone.OBSERVATIONAL,
        length_bucket="short",
        language="en",
    )
    assert meta.length_bucket == "short"


def test_post_metadata_rejects_unknown_length_bucket():
    with pytest.raises(ValidationError):
        PostMetadata(
            topics=["ai"],
            tone=Tone.OBSERVATIONAL,
            length_bucket="tiny",
            language="en",
        )
