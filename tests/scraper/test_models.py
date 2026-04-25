from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from writer_profile.scraper.models import ScrapedPost, ScrapeConfig


def test_scraped_post_creation():
    post = ScrapedPost(
        id="123",
        author="ali_ghodsi",
        platform="linkedin",
        text="AI is transforming everything.",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        url="https://linkedin.com/posts/alighodsi-123",
        source="exa",
    )
    assert post.id == "123"
    assert post.platform == "linkedin"
    assert post.source == "exa"


def test_scraped_post_requires_url():
    with pytest.raises(ValidationError, match="url"):
        ScrapedPost(
            id="123",
            author="ali",
            platform="linkedin",
            text="test",
            created_at=datetime.now(UTC),
            source="exa",
        )


def test_scrape_config_defaults():
    config = ScrapeConfig(
        author_name="Ali Ghodsi",
        linkedin_handle="alighodsi",
    )
    assert config.max_results_per_source == 50
    assert config.youtube_queries == []
