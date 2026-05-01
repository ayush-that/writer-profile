from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from writer_api.config import settings

if TYPE_CHECKING:
    from writer_api.services.embeddings import EmbeddingClient


@dataclass
class IndexedPost:
    id: str
    text: str
    author: str
    platform: str
    source_type: str = "scraped"
    published_date: str | None = None


@dataclass
class QueryResult:
    id: str
    text: str
    author: str
    platform: str
    score: float  # similarity, higher = better
    metadata: dict = field(default_factory=dict)


class ChromaStore:
    """Wrapper around a Chroma collection that uses an external EmbeddingClient.

    Falls back to a local PersistentClient at ./.chroma when cloud creds aren't
    configured (handy for dev + tests). When `chroma_host` is set in settings,
    we use chromadb.HttpClient with the cloud auth headers.
    """

    def __init__(
        self,
        collection_name: str | None = None,
        embedding_client: EmbeddingClient | None = None,
    ) -> None:
        import chromadb

        self._collection_name = collection_name or getattr(
            settings, "chroma_collection", "ceo_posts"
        )

        if embedding_client is None:
            # Lazy import to avoid circular deps with embeddings module
            from writer_api.services.embeddings import get_embedding_client

            embedding_client = get_embedding_client()
        self._embedding_client = embedding_client

        host = getattr(settings, "chroma_host", None)
        api_key_secret = getattr(settings, "chroma_api_key", None)
        api_key = api_key_secret.get_secret_value() if api_key_secret else None
        tenant = getattr(settings, "chroma_tenant", None)
        database = getattr(settings, "chroma_database", None)

        if api_key and tenant and database:
            # Chroma Cloud — uses managed CloudClient (resolves region from tenant).
            self._client = chromadb.CloudClient(
                api_key=api_key,
                tenant=tenant,
                database=database,
            )
        elif host and api_key and tenant and database:
            self._client = chromadb.HttpClient(
                host=host,
                ssl=True,
                tenant=tenant,
                database=database,
                headers={"x-chroma-token": api_key},
            )
        else:
            self._client = chromadb.PersistentClient(path="./.chroma")

        # We pass embeddings ourselves, so disable Chroma's default embedder.
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            embedding_function=None,
        )

    # Chroma free tier has a 16,384-byte per-document limit.
    _MAX_DOC_BYTES = 15_000

    def upsert_posts(self, posts: list[IndexedPost], batch_size: int = 100) -> int:
        if not posts:
            return 0

        total = 0
        for start in range(0, len(posts), batch_size):
            batch = posts[start : start + batch_size]
            texts = [self._truncate(p.text) for p in batch]
            embeddings = self._embedding_client.embed(texts)

            ids = [p.id for p in batch]
            metadatas: list[dict[str, Any]] = []
            for p in batch:
                meta: dict[str, Any] = {
                    "author": p.author,
                    "platform": p.platform,
                    "source_type": p.source_type,
                }
                if p.published_date is not None:
                    meta["published_date"] = p.published_date
                metadatas.append(meta)

            self._collection.upsert(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            total += len(batch)

        return total

    @classmethod
    def _truncate(cls, text: str) -> str:
        encoded = text.encode("utf-8")
        if len(encoded) <= cls._MAX_DOC_BYTES:
            return text
        # Slice bytes safely to a valid utf-8 boundary.
        return encoded[: cls._MAX_DOC_BYTES].decode("utf-8", errors="ignore")

    def query(
        self,
        text: str,
        k: int = 5,
        where: dict | None = None,
    ) -> list[QueryResult]:
        embedding = self._embedding_client.embed([text])[0]

        normalized_where = self._normalize_where(where)

        kwargs: dict[str, Any] = {
            "query_embeddings": [embedding],
            "n_results": k,
        }
        if normalized_where is not None:
            kwargs["where"] = normalized_where

        try:
            raw = self._collection.query(**kwargs)
        except Exception:
            # Newer chromadb requires $and wrapping for multi-key filters; older
            # versions accept the flat form. Retry with the alternate shape.
            if normalized_where is not None and where is not None:
                kwargs["where"] = where
                raw = self._collection.query(**kwargs)
            else:
                raise

        ids_outer = raw.get("ids") or [[]]
        docs_outer = raw.get("documents") or [[]]
        metas_outer = raw.get("metadatas") or [[]]
        dists_outer = raw.get("distances") or [[]]

        ids = ids_outer[0] if ids_outer else []
        docs = docs_outer[0] if docs_outer else []
        metas = metas_outer[0] if metas_outer else []
        dists = dists_outer[0] if dists_outer else []

        results: list[QueryResult] = []
        for i, doc_id in enumerate(ids):
            meta = metas[i] if i < len(metas) and metas[i] else {}
            distance = dists[i] if i < len(dists) else 0.0
            results.append(
                QueryResult(
                    id=doc_id,
                    text=docs[i] if i < len(docs) else "",
                    author=meta.get("author", ""),
                    platform=meta.get("platform", ""),
                    score=1.0 - float(distance),
                    metadata=dict(meta),
                )
            )
        return results

    def count(self) -> int:
        return int(self._collection.count())

    def delete_by_author(self, author: str, platform: str | None = None) -> int:
        before = self.count()
        if platform is None:
            where: dict = {"author": author}
        else:
            where = {"$and": [{"author": author}, {"platform": platform}]}
        try:
            self._collection.delete(where=where)
        except Exception:
            if platform is not None:
                self._collection.delete(where={"author": author, "platform": platform})
            else:
                raise
        return max(0, before - self.count())

    @staticmethod
    def _normalize_where(where: dict | None) -> dict | None:
        """Wrap multi-key filters in $and so newer chromadb versions accept them."""
        if not where:
            return None
        # Already an operator-rooted filter ($and / $or / $eq etc.) — pass through.
        if any(k.startswith("$") for k in where):
            return where
        if len(where) <= 1:
            return where
        return {"$and": [{k: v} for k, v in where.items()]}
