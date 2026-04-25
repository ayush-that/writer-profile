from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from writer_profile.scraper.exa import ExaScraper
from writer_profile.scraper.models import ScrapedPost


@pytest.fixture
def mock_exa_result():
    """Mock Exa API result object."""
    result = MagicMock()
    result.id = "post-123"
    result.url = "https://linkedin.com/posts/alighodsi-activity-123"
    result.title = "AI Post"
    result.text = "AI is transforming industries. Here's what I learned..."
    result.published_date = "2025-01-15T10:00:00Z"
    return result


@pytest.fixture
def mock_exa_client(mock_exa_result):
    """Mock Exa client with search_and_contents."""
    client = MagicMock()
    response = MagicMock()
    response.results = [mock_exa_result]
    client.search_and_contents.return_value = response
    return client


def test_scrape_linkedin_posts(mock_exa_client, mock_exa_result):
    with patch("writer_profile.scraper.exa.Exa", return_value=mock_exa_client):
        scraper = ExaScraper(api_key="test-key")
        posts = scraper.scrape_linkedin_posts(handle="alighodsi", author="ali_ghodsi")

    assert len(posts) == 1
    assert posts[0].platform == "linkedin"
    assert posts[0].author == "ali_ghodsi"
    assert posts[0].source == "exa"
    assert "linkedin.com" in posts[0].url

    mock_exa_client.search_and_contents.assert_called_once()
    call_kwargs = mock_exa_client.search_and_contents.call_args.kwargs
    assert "linkedin.com/posts" in str(call_kwargs.get("include_domains", []))


def test_scrape_linkedin_posts_deduplicates(mock_exa_client, mock_exa_result):
    response = MagicMock()
    response.results = [mock_exa_result, mock_exa_result]  # Duplicate
    mock_exa_client.search_and_contents.return_value = response

    with patch("writer_profile.scraper.exa.Exa", return_value=mock_exa_client):
        scraper = ExaScraper(api_key="test-key")
        posts = scraper.scrape_linkedin_posts(handle="alighodsi", author="ali_ghodsi")

    assert len(posts) == 1  # Deduplicated by URL


def test_scrape_news(mock_exa_client):
    with patch("writer_profile.scraper.exa.Exa", return_value=mock_exa_client):
        scraper = ExaScraper(api_key="test-key")
        posts = scraper.scrape_news(name="Ali Ghodsi", author="ali_ghodsi")

    assert len(posts) == 1
    assert posts[0].platform == "news"

    call_kwargs = mock_exa_client.search_and_contents.call_args.kwargs
    assert call_kwargs.get("category") == "news"
