from __future__ import annotations

import logging
from dataclasses import dataclass, field

from writer_api.services.chroma_store import ChromaStore, QueryResult
from writer_api.services.exa_retriever import ExaRetriever, RetrievedContent

logger = logging.getLogger(__name__)


@dataclass
class HybridBundle:
    own_posts: list[QueryResult] = field(default_factory=list)
    web_posts: list[RetrievedContent] = field(default_factory=list)


class HybridRetriever:
    def __init__(
        self,
        chroma_store: ChromaStore | None = None,
        exa_retriever: ExaRetriever | None = None,
    ) -> None:
        self._chroma_store = chroma_store
        self._exa_retriever = exa_retriever

    def _get_chroma(self) -> ChromaStore | None:
        if self._chroma_store is None:
            try:
                self._chroma_store = ChromaStore()
            except Exception as exc:
                logger.warning("ChromaStore init failed: %s", exc)
                return None
        return self._chroma_store

    def _get_exa(self) -> ExaRetriever | None:
        if self._exa_retriever is None:
            try:
                self._exa_retriever = ExaRetriever()
            except Exception as exc:
                logger.warning("ExaRetriever init failed: %s", exc)
                return None
        return self._exa_retriever

    def retrieve(
        self,
        author: str,
        platform: str,
        topic: str,
        k_own: int = 5,
        k_web: int = 3,
    ) -> HybridBundle:
        own_posts: list[QueryResult] = []
        web_posts: list[RetrievedContent] = []

        chroma = self._get_chroma()
        if chroma is not None:
            try:
                own_posts = chroma.query(
                    text=topic,
                    k=k_own,
                    where={"author": author},
                )
            except Exception as exc:
                logger.warning("Chroma query failed for %s: %s", author, exc)

        exa = self._get_exa()
        if exa is not None:
            try:
                web_posts = exa.search_for_generation(
                    author_name=author,
                    platform=platform,
                    topic=topic,
                    k=k_web,
                )
            except Exception as exc:
                logger.warning("Exa search failed for %s/%s: %s", author, platform, exc)

        return HybridBundle(own_posts=own_posts, web_posts=web_posts)
