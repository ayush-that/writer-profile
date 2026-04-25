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
