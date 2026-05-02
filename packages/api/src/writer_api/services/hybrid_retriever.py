from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from writer_api.services.chroma_store import ChromaStore, QueryResult
from writer_api.services.exa_retriever import ExaRetriever, RetrievedContent

logger = logging.getLogger(__name__)

_WS = re.compile(r"\s+")


def _trigrams(text: str) -> set[str]:
    s = _WS.sub(" ", text.lower()).strip()
    if len(s) < 3:
        return {s}
    return {s[i : i + 3] for i in range(len(s) - 2)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _diversify(results: list[QueryResult], k: int, threshold: float = 0.7) -> list[QueryResult]:
    ranked = sorted(results, key=lambda r: -r.score)
    kept: list[QueryResult] = []
    kept_grams: list[set[str]] = []
    for r in ranked:
        grams = _trigrams(r.text)
        if any(_jaccard(grams, g) > threshold for g in kept_grams):
            continue
        kept.append(r)
        kept_grams.append(grams)
        if len(kept) >= k:
            break
    return kept


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
                raw = chroma.query(
                    text=topic,
                    k=max(k_own * 2, k_own + 3),
                    where={"author": author},
                )
                own_posts = _diversify(raw, k_own)
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
