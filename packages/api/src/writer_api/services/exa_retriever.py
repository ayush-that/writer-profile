"""Exa API retriever service for searching CEO content."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from exa_py import Exa

from writer_api.config import settings


@dataclass
class RetrievedContent:
    """Content retrieved from Exa search."""

    text: str
    url: str
    title: str
    source_type: str
    published_date: datetime | None


class ExaRetriever:
    """Service for retrieving CEO content via Exa API."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the Exa retriever.

        Args:
            api_key: Exa API key. Falls back to settings if not provided.
        """
        key = api_key or settings.exa_api_key.get_secret_value()
        self._client = Exa(api_key=key)

    def search_linkedin_posts(
        self,
        author_name: str,
        linkedin_handle: str,
        max_results: int = 20,
    ) -> list[RetrievedContent]:
        """Search for LinkedIn posts by a specific author.

        Args:
            author_name: Full name of the author.
            linkedin_handle: LinkedIn handle (e.g., 'alighodsi').
            max_results: Maximum number of results to return.

        Returns:
            List of retrieved LinkedIn posts.
        """
        query = f"{linkedin_handle} {author_name}"
        results = self._client.search_and_contents(
            query=query,
            type="auto",
            num_results=max_results,
            include_domains=["linkedin.com/posts", "linkedin.com/pulse"],
            text=True,
        )
        return self._to_retrieved_content(results.results, "linkedin")

    def search_news(
        self,
        author_name: str,
        max_results: int = 20,
    ) -> list[RetrievedContent]:
        """Search for news articles and interviews about an author.

        Args:
            author_name: Full name of the author.
            max_results: Maximum number of results to return.

        Returns:
            List of retrieved news content.
        """
        query = f'"{author_name}" interview OR quote OR said'
        results = self._client.search_and_contents(
            query=query,
            type="auto",
            num_results=max_results,
            category="news",
            text=True,
        )
        return self._to_retrieved_content(results.results, "news")

    def search_for_generation(
        self,
        author_name: str,
        platform: str,
        topic: str,
        k: int = 5,
    ) -> list[RetrievedContent]:
        """Search for topic-relevant content to use as generation context.

        Args:
            author_name: Full name of the author.
            platform: Target platform (e.g., 'twitter', 'linkedin').
            topic: Topic to search for relevant content.
            k: Number of results to return.

        Returns:
            List of relevant content for generation context.
        """
        query = f'"{author_name}" {topic}'

        # Use platform-specific domain filtering
        include_domains = None
        if platform == "linkedin":
            include_domains = ["linkedin.com"]
        elif platform == "twitter":
            include_domains = ["twitter.com", "x.com"]

        search_kwargs: dict = {
            "query": query,
            "type": "auto",
            "num_results": k,
            "text": True,
        }

        if include_domains:
            search_kwargs["include_domains"] = include_domains

        results = self._client.search_and_contents(**search_kwargs)
        return self._to_retrieved_content(results.results, f"{platform}_context")

    def _to_retrieved_content(
        self,
        results: list,
        source_type: str,
    ) -> list[RetrievedContent]:
        """Convert Exa results to RetrievedContent objects.

        Args:
            results: Raw Exa search results.
            source_type: Type of source (linkedin, news, etc.).

        Returns:
            List of RetrievedContent objects.
        """
        content_list: list[RetrievedContent] = []
        for r in results:
            text = r.text or r.title or ""
            if not text.strip():
                continue

            published_date = self._parse_date(r.published_date)

            content_list.append(
                RetrievedContent(
                    text=text,
                    url=r.url or "",
                    title=r.title or "",
                    source_type=source_type,
                    published_date=published_date,
                )
            )
        return content_list

    def _parse_date(self, date_str: str | None) -> datetime | None:
        """Parse a date string to datetime.

        Args:
            date_str: ISO format date string.

        Returns:
            Parsed datetime or None if parsing fails.
        """
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            return None
