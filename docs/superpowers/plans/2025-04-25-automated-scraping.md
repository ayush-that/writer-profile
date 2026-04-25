# Automated Scraping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `writer scrape` CLI command to collect LinkedIn posts, YouTube transcripts, and news articles via Exa API.

**Architecture:** New `scraper/` module with Exa client, YouTube transcriber (yt-dlp + Whisper), and data models. CLI command orchestrates scraping and outputs JSONL for the existing ingestion pipeline.

**Tech Stack:** exa_py, yt-dlp, openai-whisper, existing Pydantic/Typer patterns

---

## File Structure

```
src/writer_profile/scraper/
├── __init__.py          # Module exports
├── models.py            # ScrapedPost, ScrapeConfig
├── exa.py               # ExaScraper class
└── youtube.py           # YouTubeTranscriber class (V2)

tests/scraper/
├── __init__.py
├── test_models.py
├── test_exa.py
└── test_youtube.py       # (V2)
```

---

### Task 1: Add dependencies to pyproject.toml

**Files:**
- Modify: `pyproject.toml:6-16`

- [ ] **Step 1: Read current dependencies**

Verify current dependencies list to understand insertion point.

- [ ] **Step 2: Add exa_py dependency**

```toml
"exa_py>=1.0.0",
```

Add after `"dotenv>=1.0.0"` in the dependencies list.

- [ ] **Step 3: Verify pyproject.toml syntax**

Run: `uv pip install -e .`
Expected: Installation succeeds without errors.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "deps: add exa_py for automated scraping"
```

---

### Task 2: Add EXA_API_KEY to Settings

**Files:**
- Modify: `src/writer_profile/config.py:14-15`
- Test: `tests/test_cli.py` (update fixture)

- [ ] **Step 1: Write failing test**

Add to `tests/test_config.py` (create if needed):

```python
import pytest
from pydantic import ValidationError

from writer_profile.config import Settings


def test_settings_requires_exa_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    with pytest.raises(ValidationError, match="exa_api_key"):
        Settings()


def test_settings_loads_exa_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    monkeypatch.setenv("EXA_API_KEY", "exa-test")
    s = Settings()
    assert s.exa_api_key.get_secret_value() == "exa-test"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with "exa_api_key" not defined.

- [ ] **Step 3: Add exa_api_key to Settings**

In `src/writer_profile/config.py`, add after line 15:

```python
exa_api_key: SecretStr = Field(alias="EXA_API_KEY")
```

- [ ] **Step 4: Update existing test fixtures**

In `tests/test_cli.py`, update `test_cli_generate_dry_run` to add:

```python
monkeypatch.setenv("EXA_API_KEY", "exa-test")
```

- [ ] **Step 5: Run all tests**

Run: `pytest -v`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/writer_profile/config.py tests/test_config.py tests/test_cli.py
git commit -m "feat(config): add EXA_API_KEY setting"
```

---

### Task 3: Create scraper data models

**Files:**
- Create: `src/writer_profile/scraper/__init__.py`
- Create: `src/writer_profile/scraper/models.py`
- Create: `tests/scraper/__init__.py`
- Create: `tests/scraper/test_models.py`

- [ ] **Step 1: Create scraper package init**

```python
# src/writer_profile/scraper/__init__.py
from writer_profile.scraper.models import ScrapedPost, ScrapeConfig

__all__ = ["ScrapedPost", "ScrapeConfig"]
```

- [ ] **Step 2: Write failing test for ScrapedPost**

Create `tests/scraper/__init__.py` (empty file).

Create `tests/scraper/test_models.py`:

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/scraper/test_models.py -v`
Expected: FAIL with import error.

- [ ] **Step 4: Implement models**

Create `src/writer_profile/scraper/models.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Platform = Literal["linkedin", "youtube", "news"]
Source = Literal["exa", "youtube_transcript"]


class ScrapedPost(BaseModel):
    id: str
    author: str = Field(min_length=1)
    platform: Platform
    text: str = Field(min_length=1)
    created_at: datetime
    url: str = Field(min_length=1)
    source: Source


class ScrapeConfig(BaseModel):
    author_name: str = Field(min_length=1)
    linkedin_handle: str = Field(min_length=1)
    youtube_queries: list[str] = Field(default_factory=list)
    max_results_per_source: int = Field(default=50, ge=1, le=100)
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/scraper/test_models.py -v`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add src/writer_profile/scraper/ tests/scraper/
git commit -m "feat(scraper): add ScrapedPost and ScrapeConfig models"
```

---

### Task 4: Implement ExaScraper class

**Files:**
- Create: `src/writer_profile/scraper/exa.py`
- Create: `tests/scraper/test_exa.py`

- [ ] **Step 1: Write failing test for ExaScraper**

Create `tests/scraper/test_exa.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/scraper/test_exa.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement ExaScraper**

Create `src/writer_profile/scraper/exa.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime

from exa_py import Exa

from writer_profile.scraper.models import ScrapedPost


class ExaScraper:
    def __init__(self, *, api_key: str) -> None:
        self._client = Exa(api_key=api_key)

    def scrape_linkedin_posts(
        self,
        *,
        handle: str,
        author: str,
        max_results: int = 50,
    ) -> list[ScrapedPost]:
        results = self._client.search_and_contents(
            query=handle,
            type="auto",
            num_results=max_results,
            include_domains=["linkedin.com/posts", "linkedin.com/pulse"],
            text=True,
        )
        return self._dedupe(self._to_posts(results.results, author, "linkedin"))

    def scrape_news(
        self,
        *,
        name: str,
        author: str,
        max_results: int = 30,
    ) -> list[ScrapedPost]:
        results = self._client.search_and_contents(
            query=name,
            type="auto",
            num_results=max_results,
            category="news",
            text=True,
        )
        return self._dedupe(self._to_posts(results.results, author, "news"))

    def scrape_youtube_urls(
        self,
        *,
        query: str,
        max_results: int = 20,
    ) -> list[dict]:
        results = self._client.search_and_contents(
            query=query,
            type="auto",
            num_results=max_results,
            include_domains=["youtube.com"],
            text=True,
        )
        return [
            {
                "url": r.url,
                "title": r.title or "",
                "published_date": r.published_date,
            }
            for r in results.results
            if r.url and "watch" in r.url
        ]

    def _to_posts(
        self,
        results: list,
        author: str,
        platform: str,
    ) -> list[ScrapedPost]:
        posts = []
        for r in results:
            text = r.text or r.title or ""
            if not text.strip():
                continue
            created = self._parse_date(r.published_date)
            posts.append(
                ScrapedPost(
                    id=r.id or r.url,
                    author=author,
                    platform=platform,
                    text=text,
                    created_at=created,
                    url=r.url,
                    source="exa",
                )
            )
        return posts

    def _parse_date(self, date_str: str | None) -> datetime:
        if not date_str:
            return datetime.now(UTC)
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(UTC)

    def _dedupe(self, posts: list[ScrapedPost]) -> list[ScrapedPost]:
        seen: set[str] = set()
        result: list[ScrapedPost] = []
        for p in posts:
            if p.url not in seen:
                seen.add(p.url)
                result.append(p)
        return result
```

- [ ] **Step 4: Update scraper __init__.py**

```python
# src/writer_profile/scraper/__init__.py
from writer_profile.scraper.exa import ExaScraper
from writer_profile.scraper.models import ScrapedPost, ScrapeConfig

__all__ = ["ExaScraper", "ScrapedPost", "ScrapeConfig"]
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/scraper/test_exa.py -v`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add src/writer_profile/scraper/exa.py src/writer_profile/scraper/__init__.py tests/scraper/test_exa.py
git commit -m "feat(scraper): implement ExaScraper for LinkedIn and news"
```

---

### Task 5: Add `writer scrape` CLI command

**Files:**
- Modify: `src/writer_profile/cli.py`
- Create: `tests/test_scrape_cli.py`

- [ ] **Step 1: Write failing test for scrape command**

Create `tests/test_scrape_cli.py`:

```python
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from writer_profile.cli import app


@pytest.fixture
def mock_scraper():
    scraper = MagicMock()
    scraper.scrape_linkedin_posts.return_value = []
    scraper.scrape_news.return_value = []
    return scraper


def test_scrape_command_exists():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert "scrape" in result.stdout


def test_scrape_dry_run(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    monkeypatch.setenv("EXA_API_KEY", "exa-test")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "scrape",
            "Ali Ghodsi",
            "--linkedin-handle", "alighodsi",
            "--output-dir", str(tmp_path),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["author_name"] == "Ali Ghodsi"
    assert payload["linkedin_handle"] == "alighodsi"
    assert payload["dry_run"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scrape_cli.py -v`
Expected: FAIL with "scrape" not found.

- [ ] **Step 3: Implement scrape command**

Add to `src/writer_profile/cli.py` after the existing imports (around line 19):

```python
from writer_profile.scraper import ExaScraper, ScrapedPost
```

Add the command after the `evaluate` command (before `if __name__`):

```python
@app.command()
def scrape(
    author_name: str = typer.Argument(..., help="Full name (e.g. 'Ali Ghodsi')"),
    linkedin_handle: str = typer.Option(..., help="LinkedIn handle (e.g. 'alighodsi')"),
    output_dir: Path = typer.Option(Path("./data"), help="Output directory for JSONL files"),
    max_linkedin: int = typer.Option(50, min=1, max=100, help="Max LinkedIn posts"),
    max_news: int = typer.Option(30, min=1, max=100, help="Max news articles"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show config without scraping"),
) -> None:
    """Scrape LinkedIn posts and news for a CEO via Exa API."""
    settings = Settings()
    author_id = author_name.lower().replace(" ", "_")

    if dry_run:
        typer.echo(
            json.dumps(
                {
                    "author_name": author_name,
                    "author_id": author_id,
                    "linkedin_handle": linkedin_handle,
                    "output_dir": str(output_dir),
                    "max_linkedin": max_linkedin,
                    "max_news": max_news,
                    "dry_run": True,
                }
            )
        )
        raise typer.Exit(0)

    output_dir.mkdir(parents=True, exist_ok=True)
    scraper = ExaScraper(api_key=settings.exa_api_key.get_secret_value())

    # Scrape LinkedIn
    typer.echo(f"Scraping LinkedIn posts for @{linkedin_handle}...")
    linkedin_posts = scraper.scrape_linkedin_posts(
        handle=linkedin_handle,
        author=author_id,
        max_results=max_linkedin,
    )
    linkedin_path = output_dir / f"{author_id}_linkedin.jsonl"
    _write_posts(linkedin_posts, linkedin_path)
    typer.echo(f"  {len(linkedin_posts)} posts → {linkedin_path}")

    # Scrape news
    typer.echo(f"Scraping news about {author_name}...")
    news_posts = scraper.scrape_news(
        name=author_name,
        author=author_id,
        max_results=max_news,
    )
    news_path = output_dir / f"{author_id}_news.jsonl"
    _write_posts(news_posts, news_path)
    typer.echo(f"  {len(news_posts)} articles → {news_path}")

    typer.echo(f"\nDone! Ingest with: writer ingest {output_dir}/{author_id}_*.jsonl --author {author_id}")


def _write_posts(posts: list[ScrapedPost], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        for p in posts:
            f.write(
                json.dumps(
                    {
                        "id": p.id,
                        "author": p.author,
                        "platform": p.platform,
                        "text": p.text,
                        "created_at": p.created_at.isoformat(),
                    }
                )
                + "\n"
            )
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_scrape_cli.py -v`
Expected: All pass.

- [ ] **Step 5: Run full test suite**

Run: `pytest -v`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/writer_profile/cli.py tests/test_scrape_cli.py
git commit -m "feat(cli): add writer scrape command for Exa-based scraping"
```

---

### Task 6: Lint and verify

**Files:**
- All modified files

- [ ] **Step 1: Run linter**

Run: `ruff check src tests --fix`
Expected: No errors (or auto-fixed).

- [ ] **Step 2: Run formatter**

Run: `ruff format src tests`
Expected: Files formatted.

- [ ] **Step 3: Run full test suite**

Run: `pytest -v`
Expected: All tests pass.

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "chore: lint and format"
```

---

## V2 Tasks (YouTube Transcription - Out of Scope for V1)

These tasks are documented for future implementation:

### Task 7 (V2): Add YouTube dependencies

- yt-dlp>=2024.0.0
- openai-whisper>=20231117

### Task 8 (V2): Implement YouTubeTranscriber class

- Download audio with yt-dlp
- Transcribe with Whisper (local)
- Return ScrapedPost objects

### Task 9 (V2): Add --youtube-queries option to scrape command

- Accept comma-separated queries
- Call YouTubeTranscriber for each video found
- Output to `{author}_youtube.jsonl`

---

## Summary

V1 delivers:
- `writer scrape "Ali Ghodsi" --linkedin-handle alighodsi` command
- LinkedIn posts via Exa `include_domains` filter
- News articles via Exa `category=news`
- JSONL output compatible with existing `writer ingest`

V2 adds:
- YouTube video discovery + Whisper transcription
