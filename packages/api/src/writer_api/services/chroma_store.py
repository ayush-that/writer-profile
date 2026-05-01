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
    score: float
    metadata: dict = field(default_factory=dict)


class ChromaStore:
    _MAX_DOC_BYTES = 15_000

    def __init__(
        self,
        collection_name: str | None = None,
        embedding_client: EmbeddingClient | None = None,
    ) -> None:
        import chromadb

        self._collection_name = collection_name or settings.chroma_collection

        if embedding_client is None:
            from writer_api.services.embeddings import get_embedding_client

            embedding_client = get_embedding_client()
        self._embedding_client = embedding_client

        api_key = (
            settings.chroma_api_key.get_secret_value()
            if settings.chroma_api_key
            else None
        )
        tenant = settings.chroma_tenant
        database = settings.chroma_database

        if api_key and tenant and database:
            self._client = chromadb.CloudClient(
                api_key=api_key,
                tenant=tenant,
                database=database,
            )
        else:
            self._client = chromadb.PersistentClient(path="./.chroma")

        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            embedding_function=None,
        )

    def upsert_posts(self, posts: list[IndexedPost], batch_size: int = 100) -> int:
        if not posts:
            return 0

        total = 0
        for start in range(0, len(posts), batch_size):
            batch = posts[start : start + batch_size]
            texts = [self._truncate(p.text) for p in batch]
            embeddings = self._embedding_client.embed(texts)

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
                ids=[p.id for p in batch],
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
        return encoded[: cls._MAX_DOC_BYTES].decode("utf-8", errors="ignore")

    def query(
        self,
        text: str,
        k: int = 5,
        where: dict | None = None,
    ) -> list[QueryResult]:
        embedding = self._embedding_client.embed([text])[0]

        kwargs: dict[str, Any] = {
            "query_embeddings": [embedding],
            "n_results": k,
        }
        normalized_where = self._normalize_where(where)
        if normalized_where is not None:
            kwargs["where"] = normalized_where

        raw = self._collection.query(**kwargs)

        ids = (raw.get("ids") or [[]])[0]
        docs = (raw.get("documents") or [[]])[0]
        metas = (raw.get("metadatas") or [[]])[0]
        dists = (raw.get("distances") or [[]])[0]

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
        self._collection.delete(where=where)
        return max(0, before - self.count())

    @staticmethod
    def _normalize_where(where: dict | None) -> dict | None:
        if not where:
            return None
        if any(k.startswith("$") for k in where):
            return where
        if len(where) <= 1:
            return where
        return {"$and": [{k: v} for k, v in where.items()]}
